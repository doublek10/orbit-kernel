"""
Workflow Engine

Coordinates business processes that operate on an ALREADY-resolved
ExecutionContext (auth bootstrapping - signup/login - is handled
separately in kernel_api/auth_routes.py, since it's what creates that
context in the first place).

Every request the Gateway forwards to /kernel/v1/execute lands here and
is dispatched by name to a handler below. Each handler is deterministic
and repeatable, and ends by publishing an event per Development Rule #7
(auditing itself already happens one layer up, in kernel_api/routes.py).
"""

import hashlib
import json
import secrets

import asyncpg
from fastapi import HTTPException

from shared.config import get_settings

from financial_graph.graph import FinancialGraph
from kernel.company_blueprint import (
    CANONICAL_FIELDS,
    SUPPORTED_LANGUAGES,
    ApiGeneratorStore,
    BlueprintLoader,
    BlueprintValidationError,
    MappingStore,
    MappingValidationError,
    SchemaStore,
    SchemaValidationError,
    VersionManager,
    apply_mapping,
    get_security_overview,
    recommended_financial_categories,
    recommended_system_types,
    relevant_app_categories,
    relevant_insight_ids,
    render_sdk,
    sign_payload,
    validate_event,
    validate_field_rules,
    verify_signature,
)
from kernel.company_blueprint.encryption import encrypt_secret
from kernel.event_bus.bus import get_event_bus
from kernel.intelligence_engine.manager import get_intelligence_manager
from kernel.provider_manager import catalog as provider_catalog
from kernel.integration_manager import catalog as integration_catalog
from kernel.provider_manager.manager import get_provider_manager
from kernel.workflow_engine.automation import WorkflowAutomation
from marketplace.catalog import CATALOG
from country_packages.registry import get_country_package
from providers.csv_import.parser import parse_statement_csv
from ai.insights import AIInsights
from replay.simulator import ReplaySimulator

LARGE_TRANSACTION_AUTOMATION_NAME = "Large transaction alert (from Blueprint)"

EXAMPLE_EVENT_NAMES = [
    "payment.received",
    "invoice.created",
    "invoice.paid",
    "expense.created",
    "inventory.updated",
    "salary.processed",
]


class WorkflowEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._graph = FinancialGraph(pool)
        self._events = get_event_bus(pool)
        self._providers = get_provider_manager()
        self._automation = WorkflowAutomation(pool)
        self._ai = AIInsights(pool)
        self._replay = ReplaySimulator(pool)
        self._blueprint = VersionManager(pool)
        self._blueprint_loader = BlueprintLoader(pool)
        self._mappings = MappingStore(pool)
        self._schemas = SchemaStore(pool)
        self._api_generator = ApiGeneratorStore(pool)
        self._intelligence = get_intelligence_manager(pool)
        self._handlers = {
            "dashboard.list": self._dashboard_overview,
            "dashboard.overview": self._dashboard_overview,
            "intelligence_dashboard.list": self._intelligence_dashboard,
            "intelligence_reports.list": self._intelligence_reports,
            "intelligence_notifications.list": self._intelligence_notifications,
            "intelligence_notifications.create": self._intelligence_notifications_mark_read,
            "intelligence_forecast.list": self._intelligence_forecast,
            "intelligence_performance.list": self._intelligence_performance,
            "intelligence_knowledge.list": self._intelligence_knowledge,
            "intelligence_history.list": self._intelligence_history,
            "intelligence_status.list": self._intelligence_status,
            "intelligence_preferences.list": self._intelligence_preferences_get,
            "intelligence_preferences.create": self._intelligence_preferences_set,
            "blueprint.list": self._blueprint_get,
            "blueprint.create": self._blueprint_publish,
            "blueprint.versions": self._blueprint_versions,
            "blueprint.restore": self._blueprint_restore,
            "blueprint.compare": self._blueprint_compare,
            "mappings.list": self._mappings_list,
            "mappings.create": self._mappings_upsert,
            "mappings.delete": self._mappings_delete,
            "mappings.preview": self._mappings_preview,
            "schema.list": self._schema_list,
            "schema.create": self._schema_upsert,
            "schema.delete": self._schema_delete,
            "schema.validate": self._schema_validate,
            "schema.versions": self._schema_versions,
            "company.api_generate": self._company_api_generate,
            "company.rotate_secret": self._company_rotate_secret,
            "company.test_endpoint": self._company_test_endpoint,
            "sdk.generate": self._sdk_generate,
            "security.overview": self._security_overview,
            "graph.list": self._graph_timeline,
            "graph.create": self._graph_create,
            "providers.list": self._providers_list,
            "providers.create": self._providers_connect,
            "providers.test": self._providers_test,
            "providers.delete": self._providers_disconnect,
            "integrations.list": self._integrations_list,
            "integrations.create": self._integrations_connect,
            "integrations.test": self._integrations_test,
            "integrations.delete": self._integrations_disconnect,
            "workflows.list": self._workflows_list,
            "workflows.create": self._workflows_create,
            "companies.list": self._company_overview,
            "companies.create": self._company_add_member,
            "developer.list": self._developer_list,
            "developer.create": self._developer_dispatch,
            "marketplace.list": self._marketplace_list,
            "marketplace.create": self._marketplace_toggle,
            "enterprise.list": self._enterprise_overview,
            "ai.list": self._ai_insights,
            "replay.list": self._replay_default,
            "replay.create": self._replay_simulate,
        }

    async def run(self, ctx, workflow: str, payload: dict) -> dict:
        handler = self._handlers.get(workflow)
        if handler is None:
            raise NotImplementedError(f"Workflow '{workflow}' is not implemented yet")
        return await handler(ctx, payload or {})

    def _require_admin(self, ctx, action_description: str) -> None:
        """
        Permission Engine enforcement, applied to the handful of actions
        that can genuinely damage a business or its security if any
        member could do them: adding teammates, issuing/revoking API
        keys, installing marketplace apps. Deliberately NOT applied to
        everyday operations (recording transactions, connecting a
        provider, building automations) - there's no admin UI yet to
        grant fine-grained permissions, so gating routine work behind
        permissions nobody can assign would just lock every non-owner
        out of the product. Owner and admin roles get through; everyone
        else is turned away with a clear reason.
        """
        if not (ctx.has_permission("*") or ctx.role in ("owner", "admin")):
            raise HTTPException(403, f"Only an owner or admin can {action_description}")

    def _require_owner(self, ctx, action_description: str) -> None:
        """
        Company Blueprint Design Principle #10: "Only the Company Owner
        may modify the Blueprint" - stricter than _require_admin above.
        No administrator, manager, employee, or API consumer may publish,
        restore, or otherwise change the Blueprint - only the Owner.
        Reading it (blueprint.list / .versions / .compare) is open to
        every member; this guard is only ever applied to writes.
        """
        if ctx.role != "owner":
            raise HTTPException(403, f"Only the Company Owner can {action_description}")

    # --- company blueprint (first-login setup wizard + Blueprint Versions) --

    async def _blueprint_get(self, ctx, payload: dict) -> dict:
        blueprint = await self._blueprint_loader.load(ctx.company_id)
        return {
            "onboarded": blueprint is not None,
            "blueprint": blueprint.to_dict() if blueprint else None,
            "you_can_edit": ctx.role == "owner",
        }

    async def _blueprint_publish(self, ctx, payload: dict) -> dict:
        self._require_owner(ctx, "publish the Company Blueprint")

        try:
            blueprint = await self._blueprint.publish(
                company_id=ctx.company_id, published_by=ctx.user_id, payload=payload
            )
        except BlueprintValidationError as exc:
            raise HTTPException(422, str(exc))

        self._blueprint_loader.invalidate(ctx.company_id)
        await self._sync_blueprint_automations(ctx.company_id, blueprint)

        await self._events.publish(
            "blueprint.published",
            {"version": blueprint.version, "business_type": blueprint.business_type},
            company_id=ctx.company_id,
        )
        return {"blueprint": blueprint.to_dict()}

    async def _blueprint_versions(self, ctx, payload: dict) -> dict:
        versions = await self._blueprint.list_versions(ctx.company_id)
        return {"versions": versions}

    async def _blueprint_restore(self, ctx, payload: dict) -> dict:
        self._require_owner(ctx, "restore a previous Blueprint version")
        version = payload.get("version")
        if version is None:
            raise HTTPException(422, "version is required")

        try:
            blueprint = await self._blueprint.restore(
                company_id=ctx.company_id, published_by=ctx.user_id, version=int(version)
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc))

        self._blueprint_loader.invalidate(ctx.company_id)
        await self._sync_blueprint_automations(ctx.company_id, blueprint)

        await self._events.publish(
            "blueprint.version_restored",
            {"restored_version": version, "new_version": blueprint.version},
            company_id=ctx.company_id,
        )
        return {"blueprint": blueprint.to_dict()}

    async def _blueprint_compare(self, ctx, payload: dict) -> dict:
        from_version = payload.get("from_version")
        to_version = payload.get("to_version")
        if from_version is None or to_version is None:
            raise HTTPException(422, "from_version and to_version are required")
        try:
            return await self._blueprint.compare(
                ctx.company_id, int(from_version), int(to_version)
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc))

    async def _sync_blueprint_automations(self, company_id: str, blueprint) -> None:
        """
        The Blueprint is configuration, not logic (Design Principle #1) -
        but "notify me on large transactions" is a real business rule, so
        publishing/restoring a Blueprint keeps the Rule Engine's
        automation for it in sync, instead of just remembering a
        preference nobody acts on. Idempotent: always removes the old
        Blueprint-owned automation first, so restoring an older version
        can turn it back off just as easily as a fresh publish turns it on.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM workflow_definitions WHERE company_id = $1 AND name = $2",
                company_id,
                LARGE_TRANSACTION_AUTOMATION_NAME,
            )
        if blueprint.notify_on_large_transaction and blueprint.large_transaction_threshold is not None:
            await self._automation.create(
                company_id=company_id,
                name=LARGE_TRANSACTION_AUTOMATION_NAME,
                trigger_event="transaction.recorded",
                condition={"field": "amount", "op": "gte", "value": blueprint.large_transaction_threshold},
                action={
                    "type": "notify",
                    "message": f"Transaction at or above {blueprint.large_transaction_threshold:g} recorded",
                },
            )

    # --- data mapping (Visual JSON Mapper / Transformation Engine) ------

    async def _mappings_list(self, ctx, payload: dict) -> dict:
        mappings = await self._mappings.list_mappings(ctx.company_id)
        return {
            "mappings": [m.to_dict() for m in mappings],
            "canonical_fields": CANONICAL_FIELDS,
        }

    async def _mappings_upsert(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "save a data mapping")
        try:
            mapping = await self._mappings.upsert(
                company_id=ctx.company_id,
                created_by=ctx.user_id,
                name=payload.get("name", ""),
                field_rules=payload.get("field_rules", []),
                sample_payload=payload.get("sample_payload") or {},
            )
        except MappingValidationError as exc:
            raise HTTPException(422, str(exc))

        await self._events.publish(
            "mapping.saved", {"name": mapping.name}, company_id=ctx.company_id
        )
        return {"mapping": mapping.to_dict()}

    async def _mappings_delete(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "delete a data mapping")
        mapping_id = payload.get("id")
        if not mapping_id:
            raise HTTPException(422, "id is required")
        deleted = await self._mappings.delete(ctx.company_id, mapping_id)
        if not deleted:
            raise HTTPException(404, "Mapping not found")
        return {"deleted": True}

    async def _mappings_preview(self, ctx, payload: dict) -> dict:
        """
        Applies a mapping (saved by {id}, or ad-hoc {field_rules}) to a
        sample payload and returns the canonical event it would produce -
        the "paste JSON, see it mapped" preview the Visual JSON Mapper is
        built around. Read-only: nothing is persisted or sent to the
        Workflow Engine, this only ever previews the transform.
        """
        sample_payload = payload.get("sample_payload") or {}
        if not isinstance(sample_payload, dict):
            raise HTTPException(422, "sample_payload must be a JSON object")

        if payload.get("id"):
            mapping = await self._mappings.get(ctx.company_id, payload["id"])
            if mapping is None:
                raise HTTPException(404, "Mapping not found")
            field_rules = mapping.field_rules
        else:
            try:
                field_rules = validate_field_rules(payload.get("field_rules", []))
            except MappingValidationError as exc:
                raise HTTPException(422, str(exc))

        return apply_mapping(sample_payload, field_rules)

    # --- event schema builder (Schema Engine) ---------------------------

    async def _schema_list(self, ctx, payload: dict) -> dict:
        schemas = await self._schemas.list_schemas(ctx.company_id)
        return {
            "schemas": [s.to_dict() for s in schemas],
            "example_event_names": EXAMPLE_EVENT_NAMES,
            "rule_types": ["string", "number", "boolean"],
        }

    async def _schema_upsert(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "define an event schema")
        try:
            schema = await self._schemas.upsert(
                company_id=ctx.company_id, created_by=ctx.user_id, payload=payload
            )
        except SchemaValidationError as exc:
            raise HTTPException(422, str(exc))

        await self._events.publish(
            "schema.saved",
            {"event_name": schema.event_name, "version": schema.version},
            company_id=ctx.company_id,
        )
        return {"schema": schema.to_dict()}

    async def _schema_delete(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "delete an event schema")
        schema_id = payload.get("id")
        if not schema_id:
            raise HTTPException(422, "id is required")
        deleted = await self._schemas.delete(ctx.company_id, schema_id)
        if not deleted:
            raise HTTPException(404, "Schema not found")
        return {"deleted": True}

    async def _schema_validate(self, ctx, payload: dict) -> dict:
        """
        The Schema Engine's actual job: validate an arbitrary event
        payload against a saved schema and reject it if it doesn't fit -
        required fields present, declared types and constraints honored.
        Unknown fields are warnings, not errors (see validate_event).
        """
        schema_id = payload.get("id")
        event_payload = payload.get("payload") or {}
        if not isinstance(event_payload, dict):
            raise HTTPException(422, "payload must be a JSON object")
        if not schema_id:
            raise HTTPException(422, "id is required")

        schema = await self._schemas.get(ctx.company_id, schema_id)
        if schema is None:
            raise HTTPException(404, "Schema not found")

        return validate_event(event_payload, schema)

    async def _schema_versions(self, ctx, payload: dict) -> dict:
        schema_id = payload.get("id")
        if not schema_id:
            raise HTTPException(422, "id is required")
        versions = await self._schemas.versions(ctx.company_id, schema_id)
        return {"versions": versions}

    # --- API Generator / SDK Generator ----------------------------------

    async def _company_api_generate(self, ctx, payload: dict) -> dict:
        """
        "The Company Owner requests an Orbit endpoint." Ensures a Company
        Endpoint identity exists (slug + HMAC signing secret) and issues
        a bearer API key alongside it, reusing the existing api_keys
        mechanism rather than duplicating it. The webhook secret is only
        ever returned in the response that creates it - reading it back
        later isn't possible, same contract as the API key itself.
        """
        self._require_admin(ctx, "generate Orbit API credentials")

        endpoint, new_secret = await self._api_generator.get_or_create(ctx.company_id)
        key_result = await self._developer_create_key(
            ctx, {"name": payload.get("key_name") or "Company Endpoint Key"}
        )

        await self._events.publish(
            "company.api_generated", {"endpoint_slug": endpoint.endpoint_slug}, company_id=ctx.company_id
        )

        base_url = get_settings().gateway_public_base_url
        return {
            "endpoint": endpoint.to_dict(base_url),
            "api_key": key_result["api_key"],
            "webhook_secret": new_secret,  # None if the endpoint already existed
        }

    async def _company_rotate_secret(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "rotate the webhook signing secret")
        try:
            endpoint, new_secret = await self._api_generator.rotate(ctx.company_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc))

        await self._events.publish(
            "company.secret_rotated", {"endpoint_slug": endpoint.endpoint_slug}, company_id=ctx.company_id
        )

        base_url = get_settings().gateway_public_base_url
        return {"endpoint": endpoint.to_dict(base_url), "webhook_secret": new_secret}

    async def _company_test_endpoint(self, ctx, payload: dict) -> dict:
        """
        Test Console. Signs a sample payload with the company's real
        webhook secret, verifies that signature immediately (proving the
        mechanism end to end), generates the request-id header a real
        client would send, and optionally runs the payload through a
        saved Data Mapping to preview what would happen next. Nothing is
        persisted - live ingestion at the generated endpoint URL isn't
        built yet (see the note on gateway_public_base_url), so this is
        the honest way to exercise the credentials before that exists.
        """
        self._require_admin(ctx, "test the Orbit endpoint")

        sample_payload = payload.get("sample_payload") or {}
        if not isinstance(sample_payload, dict):
            raise HTTPException(422, "sample_payload must be a JSON object")

        secret = await self._api_generator.get_decrypted_secret(ctx.company_id)
        if secret is None:
            raise HTTPException(404, "Generate your API credentials first")

        raw_body = json.dumps(sample_payload, sort_keys=True)
        signature = sign_payload(secret, raw_body)
        verified = verify_signature(secret, raw_body, signature)
        request_id = secrets.token_hex(16)

        result = {
            "raw_body": raw_body,
            "signature": signature,
            "request_id": request_id,
            "signature_verified": verified,
        }

        if payload.get("mapping_id"):
            mapping = await self._mappings.get(ctx.company_id, payload["mapping_id"])
            if mapping is None:
                raise HTTPException(404, "Mapping not found")
            result["mapping_preview"] = apply_mapping(sample_payload, mapping.field_rules)

        return result

    async def _sdk_generate(self, ctx, payload: dict) -> dict:
        language = payload.get("language", "")
        endpoint = await self._api_generator.get(ctx.company_id)
        base_url = get_settings().gateway_public_base_url
        endpoint_url = (
            endpoint.to_dict(base_url)["endpoint_url"]
            if endpoint
            else f"{base_url}/api/ingest/YOUR_ENDPOINT_SLUG"
        )
        try:
            code = render_sdk(language, endpoint_url)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        return {"language": language, "code": code, "supported_languages": SUPPORTED_LANGUAGES}

    # --- security (overview + ownership) --------------------------------

    async def _security_overview(self, ctx, payload: dict) -> dict:
        """
        Read-only for every member - Design Principle #10 makes the
        Blueprint itself Owner-only to *edit*, but seeing your own
        security posture (who has access, whether your credentials are
        intact) isn't a Blueprint edit. Actual mutations - rotating a
        secret, revoking a key - go through the workflows that already
        own them (company.rotate_secret, developer.create with
        action=revoke), each independently Owner/admin-gated.
        """
        overview = await get_security_overview(self._pool, ctx.company_id, self._api_generator)
        overview["you"] = {"role": ctx.role, "can_edit": ctx.role in ("owner", "admin")}
        return overview

    # --- dashboard -----------------------------------------------------

    async def _dashboard_overview(self, ctx, payload: dict) -> dict:
        country_pkg = get_country_package(ctx.country)
        await self._graph.ensure_default_account(ctx.company_id, currency=country_pkg.currency)
        summary = await self._graph.balance_summary(ctx.company_id)
        health = await self._graph.health_score(ctx.company_id)
        recent = await self._graph.timeline(ctx.company_id, limit=8)
        blueprint = await self._blueprint_loader.load(ctx.company_id)

        async with self._pool.acquire() as conn:
            connections = await conn.fetch(
                "SELECT provider, display_name, status, last_synced_at "
                "FROM provider_connections WHERE company_id = $1 AND status != 'disconnected'",
                ctx.company_id,
            )

        return {
            "company": {"id": ctx.company_id, "name": ctx.company_name, "country": ctx.country},
            "summary": summary,
            "health": health,
            "recent_transactions": [t.to_dict() for t in recent],
            "connections": [
                {
                    "provider": row["provider"],
                    "display_name": row["display_name"],
                    "status": row["status"],
                    "last_synced_at": row["last_synced_at"].isoformat()
                    if row["last_synced_at"]
                    else None,
                }
                for row in connections
            ],
            "blueprint": blueprint.to_dict() if blueprint else None,
        }

    # --- Intelligence Engine (owned entirely by kernel/intelligence_engine) --
    #
    # Every handler below is a thin read/write against IntelligenceManager -
    # no business logic lives here, same boundary the Financial Graph and
    # AI Insights handlers already keep. The Engine activates itself off
    # a `blueprint.published` event (see intelligence_engine/observer.py),
    # so there is deliberately no "intelligence.activate" workflow for a
    # user to call directly (Intelligence Rule #1).

    async def _intelligence_dashboard(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_dashboard(ctx.company_id)

    async def _intelligence_reports(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_reports(
            ctx.company_id,
            report_type=payload.get("report_type"),
            limit=int(payload.get("limit", 20)),
        )

    async def _intelligence_notifications(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_notifications(
            ctx.company_id,
            unread_only=bool(payload.get("unread_only", False)),
            limit=int(payload.get("limit", 50)),
        )

    async def _intelligence_notifications_mark_read(self, ctx, payload: dict) -> dict:
        notification_id = payload.get("id")
        if not notification_id:
            raise HTTPException(422, "id is required")
        marked = await self._intelligence.mark_notification_read(ctx.company_id, notification_id)
        if not marked:
            raise HTTPException(404, "Notification not found or already read")
        return {"marked_read": True, "id": notification_id}

    async def _intelligence_forecast(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_forecast(ctx.company_id)

    async def _intelligence_performance(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_performance(ctx.company_id)

    async def _intelligence_knowledge(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_knowledge(ctx.company_id)

    async def _intelligence_history(self, ctx, payload: dict) -> dict:
        metric_key = payload.get("metric_key")
        if not metric_key:
            raise HTTPException(422, "metric_key is required (e.g. 'health_score', 'net_cash_flow_30d', 'balance')")
        return await self._intelligence.get_history(ctx.company_id, metric_key, limit=int(payload.get("limit", 90)))

    async def _intelligence_status(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_status(ctx.company_id)

    async def _intelligence_preferences_get(self, ctx, payload: dict) -> dict:
        return await self._intelligence.get_preferences(ctx.company_id)

    async def _intelligence_preferences_set(self, ctx, payload: dict) -> dict:
        # Backs both POST /api/intelligence/preferences and PUT
        # /api/intelligence/settings on the Gateway - "preferences" and
        # "settings" are the same underlying concept (what the company
        # wants notified about, and how loudly), so this deliberately
        # isn't split into two divergent stores.
        self._require_admin(ctx, "change Intelligence notification preferences")
        try:
            preferences = await self._intelligence.set_preferences(ctx.company_id, payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        return {"preferences": preferences}

    # --- financial graph / ledger --------------------------------------

    async def _graph_timeline(self, ctx, payload: dict) -> dict:
        limit = int(payload.get("limit", 50))
        offset = int(payload.get("offset", 0))
        transactions = await self._graph.timeline(ctx.company_id, limit=limit, offset=offset)
        return {"transactions": [t.to_dict() for t in transactions], "limit": limit, "offset": offset}

    async def _graph_create(self, ctx, payload: dict) -> dict:
        if "csv_text" in payload:
            return await self._graph_import_csv(ctx, payload)

        account_id = payload.get("account_id") or await self._graph.ensure_default_account(
            ctx.company_id, currency=get_country_package(ctx.country).currency
        )
        transaction = await self._graph.record_transaction(
            company_id=ctx.company_id,
            account_id=account_id,
            direction=payload["direction"],
            amount=float(payload["amount"]),
            currency=payload.get("currency", get_country_package(ctx.country).currency),
            description=payload.get("description", ""),
            counterparty=payload.get("counterparty"),
            category=payload.get("category"),
            source="manual",
        )
        await self._events.publish(
            "transaction.recorded", transaction.to_dict(), company_id=ctx.company_id
        )
        triggered = await self._automation.evaluate_and_run(
            ctx.company_id, "transaction.recorded", transaction.to_dict()
        )
        return {"transaction": transaction.to_dict(), "automations_triggered": triggered}

    async def _graph_import_csv(self, ctx, payload: dict) -> dict:
        """
        A real, working provider path: parses a bank/mobile money CSV
        statement the person pastes or uploads and ingests it the same
        way a live provider sync would - no external credentials needed,
        because this data already came from the person themselves.
        """
        rows, errors = parse_statement_csv(payload["csv_text"])
        account_id = payload.get("account_id") or await self._graph.ensure_default_account(
            ctx.company_id, currency=get_country_package(ctx.country).currency
        )
        currency = get_country_package(ctx.country).currency

        imported = 0
        automations_triggered = 0
        for row in rows:
            transaction = await self._graph.record_transaction(
                company_id=ctx.company_id,
                account_id=account_id,
                direction=row["direction"],
                amount=row["amount"],
                currency=currency,
                description=row["description"],
                source="csv_import",
                occurred_at=row["occurred_at"],
            )
            imported += 1
            triggered = await self._automation.evaluate_and_run(
                ctx.company_id, "transaction.recorded", transaction.to_dict()
            )
            automations_triggered += len(triggered)

        await self._events.publish(
            "ledger.csv_imported",
            {"imported": imported, "errors": len(errors)},
            company_id=ctx.company_id,
        )
        return {
            "imported": imported,
            "skipped": len(errors),
            "errors": errors[:20],  # cap - a malformed file shouldn't return a novel
            "automations_triggered": automations_triggered,
        }

    # --- providers (Financial Connections) --------------------------------

    async def _providers_list(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, provider, display_name, status, category, country, auth_method,
                       webhook_url, connected_at, last_synced_at,
                       (credentials_encrypted != '{}'::jsonb) AS has_credentials,
                       (signing_secret_encrypted IS NOT NULL) AS has_signing_secret,
                       (refresh_token_encrypted IS NOT NULL) AS has_refresh_token
                FROM provider_connections
                WHERE company_id = $1 AND status != 'disconnected'
                ORDER BY connected_at DESC
                """,
                ctx.company_id,
            )
        connected_providers = {row["provider"] for row in rows}

        blueprint = await self._blueprint_loader.load(ctx.company_id)
        recommended_categories = recommended_financial_categories(
            blueprint.business_type if blueprint else None
        )

        return {
            "connected": [
                {
                    "id": str(row["id"]),
                    "provider": row["provider"],
                    "display_name": row["display_name"],
                    "status": row["status"],
                    "category": row["category"],
                    "country": row["country"],
                    "auth_method": row["auth_method"],
                    "webhook_url": row["webhook_url"],
                    "has_credentials": row["has_credentials"],
                    "has_signing_secret": row["has_signing_secret"],
                    "has_refresh_token": row["has_refresh_token"],
                    "connected_at": row["connected_at"].isoformat(),
                    "last_synced_at": row["last_synced_at"].isoformat()
                    if row["last_synced_at"]
                    else None,
                }
                for row in rows
            ],
            "categories": provider_catalog.CATEGORIES,
            "catalog": [
                {
                    "provider": entry.provider,
                    "display_name": entry.display_name,
                    "category": entry.category,
                    "countries": entry.countries,
                    "auth_method": entry.auth_method,
                    "credential_fields": entry.credential_fields,
                    "connected": entry.provider in connected_providers,
                    "recommended": entry.category in recommended_categories,
                }
                for entry in provider_catalog.catalog_for_country(ctx.country)
            ],
        }

    async def _providers_connect(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "connect a financial provider")

        provider_name = payload.get("provider", "")
        entry = provider_catalog.get_catalog_entry(provider_name)
        if entry is None:
            raise HTTPException(
                422, f"Unknown provider '{provider_name}' - pick one from the catalog"
            )

        credentials: dict = payload.get("credentials") or {}
        missing = [f for f in entry.credential_fields if not credentials.get(f)]
        if missing:
            raise HTTPException(422, f"Missing required credential fields: {missing}")

        encrypted_credentials = {k: encrypt_secret(str(v)) for k, v in credentials.items()}
        signing_secret = payload.get("signing_secret")
        refresh_token = payload.get("refresh_token")

        account_id = await self._graph.ensure_default_account(
            ctx.company_id, currency=get_country_package(ctx.country).currency
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO provider_connections
                    (company_id, provider, display_name, status, account_id, category, country,
                     auth_method, credentials_encrypted, webhook_url, signing_secret_encrypted,
                     refresh_token_encrypted, metadata)
                VALUES ($1, $2, $3, 'connected', $4, $5, $6, $7, $8::jsonb, $9, $10, $11, $12::jsonb)
                ON CONFLICT (company_id, provider) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    status = 'connected',
                    category = EXCLUDED.category,
                    country = EXCLUDED.country,
                    auth_method = EXCLUDED.auth_method,
                    credentials_encrypted = EXCLUDED.credentials_encrypted,
                    webhook_url = EXCLUDED.webhook_url,
                    signing_secret_encrypted = EXCLUDED.signing_secret_encrypted,
                    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    metadata = EXCLUDED.metadata,
                    disconnected_at = NULL
                RETURNING id
                """,
                ctx.company_id,
                provider_name,
                payload.get("display_name") or entry.display_name,
                account_id,
                entry.category,
                payload.get("country", ctx.country),
                entry.auth_method,
                encrypted_credentials,
                payload.get("webhook_url"),
                encrypt_secret(signing_secret) if signing_secret else None,
                encrypt_secret(refresh_token) if refresh_token else None,
                payload.get("metadata") or {},
            )
        connection_id = str(row["id"])

        created = 0
        automations_triggered = 0
        if entry.live:
            # Only the sandbox adapter is actually wired up end to end -
            # pull in its transaction history so the ledger has real data
            # the moment a company connects it. Every other catalog entry
            # stores real, encrypted credentials but doesn't fabricate a
            # sync until a real adapter exists for it.
            connect_result = await self._providers.call(
                provider_name, "connect", {"company_id": ctx.company_id}
            )
            sync_result = await self._providers.call(
                provider_name,
                "sync",
                {"company_id": ctx.company_id, "currency": get_country_package(ctx.country).currency},
            )
            for tx in sync_result["transactions"]:
                transaction = await self._graph.record_transaction(
                    company_id=ctx.company_id,
                    account_id=account_id,
                    connection_id=connection_id,
                    direction=tx["direction"],
                    amount=tx["amount"],
                    currency=tx.get("currency", get_country_package(ctx.country).currency),
                    description=tx.get("description", ""),
                    counterparty=tx.get("counterparty"),
                    category=tx.get("category"),
                    source="provider_sync",
                    occurred_at=tx.get("occurred_at"),
                )
                created += 1
                triggered = await self._automation.evaluate_and_run(
                    ctx.company_id, "transaction.recorded", transaction.to_dict()
                )
                automations_triggered += len(triggered)

            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE provider_connections SET last_synced_at = now() WHERE id = $1",
                    connection_id,
                )

        await self._events.publish(
            "provider.connected",
            {"provider": provider_name, "category": entry.category, "transactions_synced": created},
            company_id=ctx.company_id,
        )

        return {
            "connection": {"id": connection_id, "provider": provider_name, "status": "connected"},
            "transactions_synced": created,
            "automations_triggered": automations_triggered,
            "live_sync_available": entry.live,
        }

    async def _providers_test(self, ctx, payload: dict) -> dict:
        """
        Test Connection. Two shapes: {id} to re-test an already-saved
        connection, or {provider, credentials} to test before saving.
        For the one live adapter this actually attempts a connection; for
        everything else it's an honest structural check - the credential
        fields the provider needs are present - not a fabricated "verified".
        """
        self._require_admin(ctx, "test a financial provider connection")

        provider_name = payload.get("provider")
        credential_keys: list[str] = []

        if payload.get("id"):
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT provider, credentials_encrypted FROM provider_connections "
                    "WHERE id = $1 AND company_id = $2",
                    payload["id"],
                    ctx.company_id,
                )
            if row is None:
                raise HTTPException(404, "Connection not found")
            provider_name = row["provider"]
            credential_keys = list(row["credentials_encrypted"].keys())
        else:
            credential_keys = list((payload.get("credentials") or {}).keys())

        entry = provider_catalog.get_catalog_entry(provider_name or "")
        if entry is None:
            raise HTTPException(422, f"Unknown provider '{provider_name}'")

        missing = [f for f in entry.credential_fields if f not in credential_keys]

        if entry.live:
            result = await self._providers.call(
                provider_name, "connect", {"company_id": ctx.company_id}
            )
            return {"ok": True, "verified": "live", "status": result.get("status", "connected")}

        if missing:
            return {
                "ok": False,
                "verified": "structural",
                "missing_fields": missing,
                "message": "Some required credential fields are missing.",
            }
        return {
            "ok": True,
            "verified": "structural",
            "message": "Credential fields look complete. Live verification isn't available for "
            "this provider yet.",
        }

    async def _providers_disconnect(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "disconnect a financial provider")
        connection_id = payload.get("id")
        if not connection_id:
            raise HTTPException(422, "id is required")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE provider_connections
                SET status = 'disconnected',
                    disconnected_at = now(),
                    credentials_encrypted = '{}'::jsonb,
                    signing_secret_encrypted = NULL,
                    refresh_token_encrypted = NULL
                WHERE id = $1 AND company_id = $2
                RETURNING provider
                """,
                connection_id,
                ctx.company_id,
            )
        if row is None:
            raise HTTPException(404, "Connection not found")

        await self._events.publish(
            "provider.disconnected", {"provider": row["provider"]}, company_id=ctx.company_id
        )
        return {"disconnected": True, "provider": row["provider"]}

    # --- business systems (Connection Manager) -----------------------------

    async def _integrations_list(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, provider, display_name, system_type, status, health, auth_method,
                       connected_at, last_synced_at,
                       (credentials_encrypted != '{}'::jsonb) AS has_credentials
                FROM business_system_connections
                WHERE company_id = $1 AND status != 'disconnected'
                ORDER BY connected_at DESC
                """,
                ctx.company_id,
            )
        connected_providers = {row["provider"] for row in rows}

        blueprint = await self._blueprint_loader.load(ctx.company_id)
        recommended_types = recommended_system_types(blueprint.business_type if blueprint else None)

        return {
            "connected": [
                {
                    "id": str(row["id"]),
                    "provider": row["provider"],
                    "display_name": row["display_name"],
                    "system_type": row["system_type"],
                    "status": row["status"],
                    "health": row["health"],
                    "authentication": row["auth_method"],
                    "has_credentials": row["has_credentials"],
                    "connected_at": row["connected_at"].isoformat(),
                    "last_synced_at": row["last_synced_at"].isoformat()
                    if row["last_synced_at"]
                    else None,
                }
                for row in rows
            ],
            "system_types": integration_catalog.SYSTEM_TYPES,
            "catalog": [
                {
                    "provider": entry.provider,
                    "display_name": entry.display_name,
                    "system_type": entry.system_type,
                    "auth_method": entry.auth_method,
                    "credential_fields": entry.credential_fields,
                    "connected": entry.provider in connected_providers,
                    "recommended": entry.system_type in recommended_types,
                }
                for entry in integration_catalog.INTEGRATION_CATALOG
            ],
        }

    async def _integrations_connect(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "connect a business system")

        provider_name = payload.get("provider", "")
        entry = integration_catalog.get_catalog_entry(provider_name)
        if entry is None:
            raise HTTPException(
                422, f"Unknown business system '{provider_name}' - pick one from the catalog"
            )

        credentials: dict = payload.get("credentials") or {}
        missing = [f for f in entry.credential_fields if not credentials.get(f)]
        if missing:
            raise HTTPException(422, f"Missing required credential fields: {missing}")

        encrypted_credentials = {k: encrypt_secret(str(v)) for k, v in credentials.items()}

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO business_system_connections
                    (company_id, provider, display_name, system_type, status, health,
                     auth_method, credentials_encrypted, metadata)
                VALUES ($1, $2, $3, $4, 'connected', 'healthy', $5, $6::jsonb, $7::jsonb)
                ON CONFLICT (company_id, provider) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    system_type = EXCLUDED.system_type,
                    status = 'connected',
                    health = 'healthy',
                    auth_method = EXCLUDED.auth_method,
                    credentials_encrypted = EXCLUDED.credentials_encrypted,
                    metadata = EXCLUDED.metadata,
                    disconnected_at = NULL
                RETURNING id
                """,
                ctx.company_id,
                provider_name,
                payload.get("display_name") or entry.display_name,
                entry.system_type,
                entry.auth_method,
                encrypted_credentials,
                payload.get("metadata") or {},
            )
        connection_id = str(row["id"])

        await self._events.publish(
            "integration.connected",
            {"provider": provider_name, "system_type": entry.system_type},
            company_id=ctx.company_id,
        )

        return {
            "connection": {
                "id": connection_id,
                "provider": provider_name,
                "system_type": entry.system_type,
                "status": "connected",
                "health": "healthy",
            }
        }

    async def _integrations_test(self, ctx, payload: dict) -> dict:
        """
        Same honesty contract as providers.test: no live adapter exists
        for any Business System yet, so this only verifies the declared
        credential fields are present, and updates the stored `health`
        to reflect that - not a fabricated live check.
        """
        self._require_admin(ctx, "test a business system connection")

        provider_name = payload.get("provider")
        connection_id = payload.get("id")
        credential_keys: list[str] = []

        if connection_id:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT provider, credentials_encrypted FROM business_system_connections "
                    "WHERE id = $1 AND company_id = $2",
                    connection_id,
                    ctx.company_id,
                )
            if row is None:
                raise HTTPException(404, "Connection not found")
            provider_name = row["provider"]
            credential_keys = list(row["credentials_encrypted"].keys())
        else:
            credential_keys = list((payload.get("credentials") or {}).keys())

        entry = integration_catalog.get_catalog_entry(provider_name or "")
        if entry is None:
            raise HTTPException(422, f"Unknown business system '{provider_name}'")

        missing = [f for f in entry.credential_fields if f not in credential_keys]
        ok = not missing
        health = "healthy" if ok else "unhealthy"

        if connection_id:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE business_system_connections SET health = $1 WHERE id = $2",
                    health,
                    connection_id,
                )

        if not ok:
            return {
                "ok": False,
                "verified": "structural",
                "missing_fields": missing,
                "message": "Some required credential fields are missing.",
            }
        return {
            "ok": True,
            "verified": "structural",
            "message": "Credential fields look complete. Live verification isn't available for "
            "this system yet.",
        }

    async def _integrations_disconnect(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "disconnect a business system")
        connection_id = payload.get("id")
        if not connection_id:
            raise HTTPException(422, "id is required")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE business_system_connections
                SET status = 'disconnected',
                    disconnected_at = now(),
                    health = 'unknown',
                    credentials_encrypted = '{}'::jsonb
                WHERE id = $1 AND company_id = $2
                RETURNING provider
                """,
                connection_id,
                ctx.company_id,
            )
        if row is None:
            raise HTTPException(404, "Connection not found")

        await self._events.publish(
            "integration.disconnected", {"provider": row["provider"]}, company_id=ctx.company_id
        )
        return {"disconnected": True, "provider": row["provider"]}

    # --- workflow catalog (introspective, honest about what's real) ----

    async def _workflows_list(self, ctx, payload: dict) -> dict:
        automations = await self._automation.list_definitions(ctx.company_id)
        recent_runs = await self._automation.recent_runs(ctx.company_id, limit=15)
        return {
            "automations": [
                {**a.to_dict(), "source": "blueprint" if a.name == LARGE_TRANSACTION_AUTOMATION_NAME else "manual"}
                for a in automations
            ],
            "recent_runs": recent_runs,
            "capabilities": [
                {"name": "dashboard.list", "status": "available", "description": "Cash position, health score, recent activity"},
                {"name": "blueprint.list", "status": "available", "description": "Read the company's active Blueprint (first-login setup)"},
                {"name": "blueprint.create", "status": "available", "description": "Publish the Company Blueprint - Owner only"},
                {"name": "blueprint.versions", "status": "available", "description": "List Blueprint version history"},
                {"name": "blueprint.restore", "status": "available", "description": "Restore a previous Blueprint version - Owner only"},
                {"name": "blueprint.compare", "status": "available", "description": "Field-level diff between two Blueprint versions"},
                {"name": "mappings.list", "status": "available", "description": "List saved data mappings and the canonical field vocabulary"},
                {"name": "mappings.create", "status": "available", "description": "Save a Visual JSON Mapper mapping (source path -> canonical field)"},
                {"name": "mappings.delete", "status": "available", "description": "Delete a saved data mapping"},
                {"name": "mappings.preview", "status": "available", "description": "Preview what a mapping produces for a sample JSON payload"},
                {"name": "schema.list", "status": "available", "description": "List saved event schemas and example event names"},
                {"name": "schema.create", "status": "available", "description": "Define an event schema - required/optional fields and validation rules"},
                {"name": "schema.delete", "status": "available", "description": "Delete an event schema"},
                {"name": "schema.validate", "status": "available", "description": "Validate a payload against a saved event schema"},
                {"name": "schema.versions", "status": "available", "description": "List an event schema's version history"},
                {"name": "company.api_generate", "status": "available", "description": "Generate the Company Endpoint identity, an API key, and a webhook signing secret"},
                {"name": "company.rotate_secret", "status": "available", "description": "Rotate the webhook signing secret"},
                {"name": "company.test_endpoint", "status": "available", "description": "Test Console - sign and verify a sample payload, optionally preview a mapping"},
                {"name": "sdk.generate", "status": "available", "description": "Generate starter code (TypeScript, JavaScript, PHP, Python, Java) for the Company Endpoint"},
                {"name": "security.overview", "status": "available", "description": "API keys, webhook credential status, ownership, and recent activity in one view"},
                {"name": "graph.list", "status": "available", "description": "Full ledger timeline"},
                {"name": "graph.create", "status": "available", "description": "Record a manual transaction"},
                {"name": "providers.list", "status": "available", "description": "List connected providers and the Financial Connections catalog"},
                {"name": "providers.create", "status": "available", "description": "Connect a financial provider with encrypted credentials"},
                {"name": "providers.test", "status": "available", "description": "Test Connection - verify or structurally validate a provider's credentials"},
                {"name": "providers.delete", "status": "available", "description": "Disconnect a provider and purge its stored credentials"},
                {"name": "integrations.list", "status": "available", "description": "List connected Business Systems and the catalog (payroll, accounting, inventory, CRM, ERP, warehouse, POS, HR)"},
                {"name": "integrations.create", "status": "available", "description": "Connect a Business System with encrypted credentials"},
                {"name": "integrations.test", "status": "available", "description": "Test Connection for a Business System"},
                {"name": "integrations.delete", "status": "available", "description": "Disconnect a Business System and purge its stored credentials"},
                {"name": "workflows.list", "status": "available", "description": "List automations and recent runs"},
                {"name": "workflows.create", "status": "available", "description": "Define a trigger \u2192 condition \u2192 action automation"},
                {"name": "ai.list", "status": "available", "description": "Statistical financial insights (health, trend, spend, anomalies, forecast), prioritized by your Blueprint"},
                {"name": "intelligence_dashboard.list", "status": "available", "description": "Intelligence Engine dashboard - status, health, findings, forecast, unread counts"},
                {"name": "intelligence_reports.list", "status": "available", "description": "Automatically generated daily/weekly/monthly/quarterly reports"},
                {"name": "intelligence_notifications.list", "status": "available", "description": "Intelligence notifications, optionally unread-only"},
                {"name": "intelligence_notifications.create", "status": "available", "description": "Mark an Intelligence notification as read"},
                {"name": "intelligence_forecast.list", "status": "available", "description": "Deterministic 30/90 day cash forecast"},
                {"name": "intelligence_performance.list", "status": "available", "description": "Continuous analysis findings plus latest tracked metrics"},
                {"name": "intelligence_knowledge.list", "status": "available", "description": "The company's Knowledge Graph (nodes and relationships)"},
                {"name": "intelligence_history.list", "status": "available", "description": "Trend history for one metric_key over time"},
                {"name": "intelligence_status.list", "status": "available", "description": "Intelligence Engine lifecycle status for this company"},
                {"name": "intelligence_preferences.list", "status": "available", "description": "Read Intelligence notification preferences"},
                {"name": "intelligence_preferences.create", "status": "available", "description": "Set Intelligence notification preferences - owner/admin only"},
                {"name": "replay.list", "status": "available", "description": "Digital Financial Twin - current trajectory, unchanged, over 90 days"},
                {"name": "replay.create", "status": "available", "description": "Digital Financial Twin scenario simulation"},
                {"name": "marketplace.list", "status": "available", "description": "List marketplace apps, flagged with recommendations based on your Blueprint"},
                {"name": "marketplace.create", "status": "available", "description": "Install or uninstall a marketplace app"},
            ],
        }

    async def _workflows_create(self, ctx, payload: dict) -> dict:
        definition = await self._automation.create(
            company_id=ctx.company_id,
            name=payload["name"],
            trigger_event=payload.get("trigger_event", "transaction.recorded"),
            condition=payload.get("condition", {}),
            action=payload.get("action", {}),
        )
        await self._events.publish(
            "workflow.created", definition.to_dict(), company_id=ctx.company_id
        )
        return {"automation": definition.to_dict()}

    # --- companies / team -------------------------------------------------

    async def _company_overview(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            members = await conn.fetch(
                """
                SELECT u.email, u.full_name, cm.role, cm.created_at
                FROM company_members cm
                JOIN users u ON u.id = cm.user_id
                WHERE cm.company_id = $1
                ORDER BY cm.created_at ASC
                """,
                ctx.company_id,
            )
        return {
            "company": {"id": ctx.company_id, "name": ctx.company_name, "country": ctx.country},
            "you": {"email": ctx.email, "role": ctx.role, "permissions": ctx.permissions},
            "members": [
                {
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "role": row["role"],
                    "joined_at": row["created_at"].isoformat(),
                }
                for row in members
            ],
        }

    async def _company_add_member(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "add members")

        email = payload.get("email", "").strip().lower()
        if not email:
            raise ValueError("email is required")

        async with self._pool.acquire() as conn:
            user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
            if user is None:
                # Honest limitation: there's no invite-by-email flow yet
                # (that needs outbound email, which isn't wired up). The
                # person has to sign up for Orbit first, then they can be
                # added to this company.
                raise ValueError(
                    f"No Orbit account found for {email} yet - they need to sign up first."
                )
            role = payload.get("role", "member")
            await conn.execute(
                """
                INSERT INTO company_members (user_id, company_id, role, permissions)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, company_id) DO UPDATE SET role = EXCLUDED.role
                """,
                user["id"],
                ctx.company_id,
                role,
                [] if role != "owner" else ["*"],
            )

        await self._events.publish(
            "company.member_added", {"email": email, "role": role}, company_id=ctx.company_id
        )
        return {"member": {"email": email, "role": role}}

    # --- developer platform / API keys -------------------------------------

    async def _developer_list(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, key_prefix, created_at, last_used_at, revoked
                FROM api_keys
                WHERE company_id = $1
                ORDER BY created_at DESC
                """,
                ctx.company_id,
            )
        return {
            "api_keys": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "key_prefix": row["key_prefix"],
                    "created_at": row["created_at"].isoformat(),
                    "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
                    "revoked": row["revoked"],
                }
                for row in rows
            ]
        }

    async def _developer_dispatch(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "manage API keys")
        if payload.get("action") == "revoke":
            return await self._developer_revoke(ctx, payload)
        return await self._developer_create_key(ctx, payload)

    async def _developer_create_key(self, ctx, payload: dict) -> dict:
        name = payload.get("name", "").strip() or "Unnamed key"
        # Real bearer token, shown exactly once - only its sha256 hash and
        # its first 8 characters (for identification in the UI) are ever
        # persisted. This mirrors how Stripe/GitHub keys work.
        raw_key = f"orbit_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO api_keys (company_id, name, key_prefix, key_hash, created_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, created_at
                """,
                ctx.company_id,
                name,
                raw_key[:14],
                key_hash,
                ctx.user_id,
            )
        await self._events.publish(
            "api_key.created", {"name": name, "key_id": str(row["id"])}, company_id=ctx.company_id
        )
        return {
            "api_key": {
                "id": str(row["id"]),
                "name": name,
                "key_prefix": raw_key[:14],
                "created_at": row["created_at"].isoformat(),
                "secret": raw_key,  # only ever present in this one response
            }
        }

    async def _developer_revoke(self, ctx, payload: dict) -> dict:
        key_id = payload.get("key_id")
        if not key_id:
            raise ValueError("key_id is required to revoke a key")
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE api_keys SET revoked = true WHERE id = $1 AND company_id = $2",
                key_id,
                ctx.company_id,
            )
        await self._events.publish("api_key.revoked", {"key_id": key_id}, company_id=ctx.company_id)
        return {"revoked": key_id}

    # --- marketplace ---------------------------------------------------

    async def _marketplace_list(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT app_key, installed_at FROM company_installed_apps WHERE company_id = $1",
                ctx.company_id,
            )
        installed = {row["app_key"]: row["installed_at"].isoformat() for row in rows}

        blueprint = await self._blueprint_loader.load(ctx.company_id)
        recommended_categories = relevant_app_categories(blueprint.priorities if blueprint else [])

        return {
            "apps": [
                {
                    **app,
                    "installed": app["app_key"] in installed,
                    "installed_at": installed.get(app["app_key"]),
                    "recommended": app["category"] in recommended_categories,
                }
                for app in CATALOG
            ]
        }

    async def _marketplace_toggle(self, ctx, payload: dict) -> dict:
        self._require_admin(ctx, "install or uninstall marketplace apps")
        app_key = payload.get("app_key")
        if app_key not in {app["app_key"] for app in CATALOG}:
            raise ValueError(f"Unknown app '{app_key}'")
        action = payload.get("action", "install")

        async with self._pool.acquire() as conn:
            if action == "uninstall":
                await conn.execute(
                    "DELETE FROM company_installed_apps WHERE company_id = $1 AND app_key = $2",
                    ctx.company_id,
                    app_key,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO company_installed_apps (company_id, app_key)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    ctx.company_id,
                    app_key,
                )

        await self._events.publish(
            f"marketplace.{action}ed", {"app_key": app_key}, company_id=ctx.company_id
        )
        return {"app_key": app_key, "action": action}

    # --- enterprise: audit & compliance overview ------------------------

    async def _enterprise_overview(self, ctx, payload: dict) -> dict:
        async with self._pool.acquire() as conn:
            audit_rows = await conn.fetch(
                """
                SELECT al.action, al.metadata, al.created_at, u.email AS actor_email
                FROM audit_log al
                JOIN users u ON u.id = al.actor_id
                WHERE al.company_id = $1
                ORDER BY al.created_at DESC
                LIMIT 25
                """,
                ctx.company_id,
            )
            counts = await conn.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM company_members WHERE company_id = $1) AS members,
                    (SELECT COUNT(*) FROM api_keys WHERE company_id = $1 AND NOT revoked) AS active_keys,
                    (SELECT COUNT(*) FROM workflow_definitions WHERE company_id = $1 AND enabled) AS automations,
                    (SELECT COUNT(*) FROM company_installed_apps WHERE company_id = $1) AS installed_apps,
                    (SELECT COUNT(*) FROM provider_connections WHERE company_id = $1) AS connections
                """,
                ctx.company_id,
            )

        return {
            "summary": dict(counts),
            "audit_trail": [
                {
                    "actor_email": row["actor_email"],
                    "action": row["action"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in audit_rows
            ],
        }

    # --- AI insights -----------------------------------------------------

    async def _ai_insights(self, ctx, payload: dict) -> dict:
        insights = await self._ai.generate(ctx.company_id)

        blueprint = await self._blueprint_loader.load(ctx.company_id)
        if blueprint is not None and blueprint.priorities:
            relevant = relevant_insight_ids(blueprint.priorities)
            # Stable sort: the health score stays the headline, insights
            # matching a stated priority move up next, everything else
            # keeps its original (statistically-driven) order after that.
            insights.sort(key=lambda i: (i["id"] != "health-score", i["id"] not in relevant))

        return {"insights": insights}

    # --- replay / digital financial twin ----------------------------------

    async def _replay_default(self, ctx, payload: dict) -> dict:
        # No scenarios - just the current trajectory, unchanged, over 90 days.
        result = await self._replay.simulate(ctx.company_id, scenarios=[], horizon_days=90)
        return result

    async def _replay_simulate(self, ctx, payload: dict) -> dict:
        scenarios = payload.get("scenarios", [])
        horizon_days = int(payload.get("horizon_days", 90))
        result = await self._replay.simulate(
            ctx.company_id, scenarios=scenarios, horizon_days=horizon_days
        )
        await self._events.publish(
            "replay.simulated",
            {"scenario_count": len(scenarios), "horizon_days": horizon_days},
            company_id=ctx.company_id,
        )
        return result
