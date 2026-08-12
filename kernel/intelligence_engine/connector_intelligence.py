"""
Intelligence Engine - Connector Intelligence

This is what makes the Engine's picture of a business bigger than just
ledger_transactions: if a company has saved a Connector URL in the
Connector Generator wizard (migrations/014_connector_preferences.sql,
kernel/company_blueprint/connector_preferences.py), every Intelligence
Cycle now also reads that company's own live business data through it.

Orbit never assumes a fixed table shape here. A company's Connector
Generator wizard lets them name their own entities (connector_generator.
py's `_clean_entity` / `_clean_tables` accept any name, not just the
defaults), so this module does not hardcode "employees, invoices,
inventory, payments" - the Kernel doesn't know a company's table names
in advance and has no persisted table map to read (connector_preferences
deliberately only stores language/database/connector_url, never the
table map - see connector_preferences.py's docstring). Instead:

  1. It calls `?entity=_health` first - every generated connector file
     (JS/PHP/Python/Java, see connector_generator.py's HTTP entrypoints)
     answers that with `{"ok": true, "entities": [...]}`: the real,
     current list of entities *that company* mapped, in their own
     words.
  2. For each discovered entity it pulls a sample of live rows and
     classifies what kind of business object it looks like (invoice-
     like, inventory-like, employee-like, payment-like, or unclassified)
     from the entity's name and the fields actually present in its
     rows - never from a fixed whitelist of names.
  3. It looks for foreign-key-shaped fields (anything ending in `_id`)
     and matches them against the other entities that same connector
     reported, to describe how the company's own tables relate to each
     other (e.g. an `invoices` row's `customer_id` pointing at a
     `customers` entity) - again inferred per company, not assumed.

A company with three tables named `orders`, `stock`, and `staff` gets
exactly as much out of this as one using the wizard's own suggested
names - that's the point of calling it intelligence rather than a fixed
integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import asyncpg

from kernel.company_blueprint.connector_preferences import ConnectorPreferencesStore
from kernel.intelligence_engine.models import Finding

_READ_LIMIT = 500
_TIMEOUT = 8.0
_ALLOWED_SCHEMES = {"http", "https"}
_MAX_ENTITIES = 12  # a runaway/misconfigured _health response shouldn't hammer the connector

# Fallback only for connectors deployed before `_health` existed, or a
# hand-rolled connector that never implements it - not the primary path.
_LEGACY_FALLBACK_ENTITIES = ["employees", "invoices", "inventory", "payments"]

_PAID_TRUE = {"paid", "true", "1", "yes", "settled", "complete", "completed", "success"}
_PAID_FALSE = {"unpaid", "false", "0", "no", "pending", "overdue", "outstanding", "due", "open"}
_ACTIVE_TRUE = {"active", "true", "1", "yes", "employed", "current"}
_ACTIVE_FALSE = {"inactive", "false", "0", "no", "terminated", "left", "former", "resigned"}

_STATUS_KEYS = ("status", "state", "payment_status", "invoice_status")
_PAID_FLAG_KEYS = ("paid", "is_paid", "isPaid")
_ACTIVE_FLAG_KEYS = ("active", "is_active", "isActive", "employment_status")
_AMOUNT_KEYS = ("amount", "total", "total_amount", "value", "balance", "price")
_QUANTITY_KEYS = ("quantity", "qty", "stock", "stock_level", "in_stock", "units")
_DUE_DATE_KEYS = ("due_date", "due", "due_at")
_LOW_STOCK_THRESHOLD = 10

# Name-based classification hints - matched against the entity name
# *and*, if the name is ambiguous, against the field names actually
# present in a sample row. Order matters: first confident match wins.
_KIND_NAME_HINTS = {
    "invoice": {"invoice", "bill", "receivable"},
    "inventory": {"inventory", "stock", "product", "item", "sku", "warehouse"},
    "employee": {"employee", "staff", "payroll", "personnel", "hr_"},
    "payment": {"payment", "transaction", "receipt", "transfer", "payout"},
}
_KIND_FIELD_HINTS = {
    "invoice": {"invoice_number", "due_date", "invoice_status", "amount_due"},
    "inventory": {"quantity", "qty", "stock", "stock_level", "sku", "warehouse"},
    "employee": {"salary", "hire_date", "department", "employee_id", "job_title"},
    "payment": {"payment_method", "transaction_id", "payer", "payee"},
}


def _norm(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def _first_present(row: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key.lower() in lowered and lowered[key.lower()] is not None:
            return lowered[key.lower()]
    return None


def _to_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _singularize(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith("ies"):
        return lowered[:-3] + "y"
    if lowered.endswith("s") and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


@dataclass(frozen=True)
class ConnectorEntitySummary:
    entity: str
    kind: str
    reachable: bool
    row_count: int
    error: str | None
    summary: dict[str, Any]
    fields: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "kind": self.kind,
            "reachable": self.reachable,
            "row_count": self.row_count,
            "error": self.error,
            "summary": self.summary,
            "fields": self.fields,
        }


class ConnectorIntelligence:
    """
    Gathers live data from a company's deployed Connector URL, if one is
    saved - discovering whatever entities that connector actually
    offers rather than assuming a fixed schema - and turns it into
    (a) a per-entity summary plus inferred relationships for
    dashboards/the Compile report, and (b) Findings the Reasoning Engine
    folds in alongside the ledger-driven ones.
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._preferences = ConnectorPreferencesStore(pool)

    async def gather(self, company_id: str) -> tuple[dict[str, Any], list[Finding]]:
        preferences = await self._preferences.get(company_id)
        connector_url = (preferences.connector_url if preferences else None) or ""
        connector_url = connector_url.strip()

        if not connector_url:
            return (
                {
                    "connected": False,
                    "connector_url": None,
                    "reason": "No Connector URL saved yet - connect one in Developer \u2192 Connector Generator "
                    "so the AI can read your live business data.",
                    "entities": [],
                    "relationships": [],
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                [],
            )

        parsed = urlparse(connector_url)
        if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
            return (
                {
                    "connected": False,
                    "connector_url": connector_url,
                    "reason": "Saved Connector URL is not a valid http(s) address.",
                    "entities": [],
                    "relationships": [],
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                [],
            )

        try:
            import httpx
        except ImportError:
            return (
                {
                    "connected": False,
                    "connector_url": connector_url,
                    "reason": "httpx is not installed on this Kernel.",
                    "entities": [],
                    "relationships": [],
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                [],
            )

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            entity_names, discovered = await self._discover_entities(client, connector_url)

            entities: list[ConnectorEntitySummary] = []
            rows_by_entity: dict[str, list[dict]] = {}
            for entity_name in entity_names[:_MAX_ENTITIES]:
                summary, rows = await self._read_entity(client, connector_url, entity_name)
                entities.append(summary)
                if rows:
                    rows_by_entity[entity_name] = rows

        any_reachable = any(e.reachable for e in entities)
        relationships = self._infer_relationships(rows_by_entity)

        connector_context = {
            "connected": any_reachable,
            "connector_url": connector_url,
            "reason": None
            if any_reachable
            else "Connector URL didn't return usable data for any entity."
            if discovered
            else "Connector didn't respond to entity discovery (?entity=_health) - falling back to a "
            "generic guess at entity names. Redeploy the latest connector file to enable discovery.",
            "discovered": discovered,
            "entities": [e.to_dict() for e in entities],
            "relationships": relationships,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        findings = self._derive_findings(entities, relationships)
        return connector_context, findings

    # --- discovery -------------------------------------------------------

    async def _discover_entities(self, client, connector_url: str) -> tuple[list[str], bool]:
        """
        Asks the connector what it actually offers via `?entity=_health`
        (every generated connector answers this - see this module's
        docstring). Falls back to a small legacy guess only if that
        call fails outright, so an older deployed connector still works,
        just without the benefit of discovery.
        """
        try:
            res = await client.get(connector_url, params={"entity": "_health"})
            if res.status_code < 400:
                body = res.json()
                names = body.get("entities")
                if isinstance(names, list) and names:
                    cleaned = [str(n) for n in names if isinstance(n, (str, int)) and str(n).strip()]
                    if cleaned:
                        return cleaned, True
        except Exception:
            pass
        return list(_LEGACY_FALLBACK_ENTITIES), False

    # --- reading -------------------------------------------------------

    async def _read_entity(self, client, connector_url: str, entity: str) -> tuple[ConnectorEntitySummary, list[dict]]:
        try:
            res = await client.get(connector_url, params={"entity": entity, "limit": _READ_LIMIT})
        except Exception as exc:
            return ConnectorEntitySummary(entity, "unknown", False, 0, str(exc), {}), []

        if res.status_code >= 400:
            try:
                body = res.json()
                message = body.get("error") or f"HTTP {res.status_code}"
            except Exception:
                message = f"HTTP {res.status_code}"
            return ConnectorEntitySummary(entity, "unknown", False, 0, message, {}), []

        try:
            body = res.json()
        except Exception:
            return ConnectorEntitySummary(entity, "unknown", False, 0, "Connector did not return valid JSON.", {}), []

        if not body.get("ok", True):
            return ConnectorEntitySummary(entity, "unknown", False, 0, body.get("error") or "Connector reported an error.", {}), []

        rows = body.get("rows") or []
        if not isinstance(rows, list):
            rows = []
        rows = [r for r in rows if isinstance(r, dict)]

        kind = self._classify(entity, rows)
        summary = self._summarize(kind, rows)
        fields = sorted({k for row in rows for k in row.keys()})
        return ConnectorEntitySummary(entity, kind, True, len(rows), None, summary, fields), rows

    # --- classifying (name first, field-shape second - never a fixed list) --

    def _classify(self, entity_name: str, rows: list[dict]) -> str:
        name = _norm(entity_name)
        for kind, hints in _KIND_NAME_HINTS.items():
            if any(hint in name for hint in hints):
                return kind

        if rows:
            field_names = {str(k).lower() for row in rows[:5] for k in row.keys()}
            best_kind, best_score = "generic", 0
            for kind, hints in _KIND_FIELD_HINTS.items():
                score = len(field_names & hints)
                if score > best_score:
                    best_kind, best_score = kind, score
            if best_score > 0:
                return best_kind

        return "generic"

    # --- summarizing (heuristic, honest about what it couldn't find) ---

    def _summarize(self, kind: str, rows: list[dict]) -> dict[str, Any]:
        if kind == "invoice":
            return self._summarize_invoices(rows)
        if kind == "inventory":
            return self._summarize_inventory(rows)
        if kind == "employee":
            return self._summarize_employees(rows)
        if kind == "payment":
            return self._summarize_payments(rows)
        return self._summarize_generic(rows)

    def _summarize_generic(self, rows: list[dict]) -> dict[str, Any]:
        # No confident classification - still worth reporting that this
        # entity exists and roughly how big it is, rather than ignoring
        # any table whose name/shape Orbit didn't recognize.
        amount_field = None
        total = 0.0
        for row in rows:
            amt = _first_present(row, _AMOUNT_KEYS)
            if amt is not None:
                num = _to_number(amt)
                if num is not None:
                    amount_field = amount_field or next((k for k in _AMOUNT_KEYS if k in row), None)
                    total += num
        result: dict[str, Any] = {"row_count": len(rows)}
        if amount_field:
            result["total_amount"] = round(total, 2)
            result["amount_field"] = amount_field
        return result

    def _summarize_invoices(self, rows: list[dict]) -> dict[str, Any]:
        paid = unpaid = unknown = 0
        paid_amount = unpaid_amount = 0.0
        overdue = 0
        now = datetime.now(timezone.utc)

        for row in rows:
            is_paid = self._invoice_paid(row)
            amount = _to_number(_first_present(row, _AMOUNT_KEYS)) or 0.0

            if is_paid is True:
                paid += 1
                paid_amount += amount
            elif is_paid is False:
                unpaid += 1
                unpaid_amount += amount
                due_raw = _first_present(row, _DUE_DATE_KEYS)
                if due_raw:
                    try:
                        due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
                        if due.tzinfo is None:
                            due = due.replace(tzinfo=timezone.utc)
                        if due < now:
                            overdue += 1
                    except ValueError:
                        pass
            else:
                unknown += 1

        return {
            "row_count": len(rows),
            "paid_count": paid,
            "unpaid_count": unpaid,
            "unknown_status_count": unknown,
            "paid_amount": round(paid_amount, 2),
            "unpaid_amount": round(unpaid_amount, 2),
            "overdue_count": overdue,
        }

    @staticmethod
    def _invoice_paid(row: dict) -> bool | None:
        flag = _first_present(row, _PAID_FLAG_KEYS)
        if isinstance(flag, bool):
            return flag
        status = _norm(_first_present(row, _STATUS_KEYS) or flag)
        if status in _PAID_TRUE:
            return True
        if status in _PAID_FALSE:
            return False
        return None

    def _summarize_inventory(self, rows: list[dict]) -> dict[str, Any]:
        low_stock = []
        total_units = 0.0
        known_quantities = 0

        for row in rows:
            qty = _to_number(_first_present(row, _QUANTITY_KEYS))
            if qty is None:
                continue
            known_quantities += 1
            total_units += qty
            if qty <= _LOW_STOCK_THRESHOLD:
                name = row.get("name") or row.get("sku") or row.get("item") or row.get("product") or "item"
                low_stock.append({"item": str(name), "quantity": qty})

        return {
            "row_count": len(rows),
            "known_quantity_rows": known_quantities,
            "total_units": round(total_units, 2),
            "low_stock_count": len(low_stock),
            "low_stock_items": sorted(low_stock, key=lambda x: x["quantity"])[:10],
        }

    def _summarize_employees(self, rows: list[dict]) -> dict[str, Any]:
        active = inactive = unknown = 0
        for row in rows:
            flag = _first_present(row, _ACTIVE_FLAG_KEYS)
            if isinstance(flag, bool):
                if flag:
                    active += 1
                else:
                    inactive += 1
                continue
            status = _norm(_first_present(row, _STATUS_KEYS) or flag)
            if status in _ACTIVE_TRUE:
                active += 1
            elif status in _ACTIVE_FALSE:
                inactive += 1
            else:
                unknown += 1

        return {
            "row_count": len(rows),
            "active_count": active,
            "inactive_count": inactive,
            "unknown_status_count": unknown,
        }

    def _summarize_payments(self, rows: list[dict]) -> dict[str, Any]:
        total = 0.0
        known_amounts = 0
        for row in rows:
            amount = _to_number(_first_present(row, _AMOUNT_KEYS))
            if amount is None:
                continue
            known_amounts += 1
            total += amount

        return {
            "row_count": len(rows),
            "known_amount_rows": known_amounts,
            "total_amount": round(total, 2),
        }

    # --- relationships (how the company's own tables link together) ---

    def _infer_relationships(self, rows_by_entity: dict[str, list[dict]]) -> list[dict[str, Any]]:
        """
        Looks for foreign-key-shaped fields (anything ending in `_id`,
        other than the row's own `id`) in each entity's sample rows and
        matches them against the *other* entities this same connector
        reported, by name. This is deliberately conservative - it only
        reports a link when the field name plausibly names another
        entity that's actually present, never a guess dressed up as a
        fact.
        """
        entity_names = {_singularize(name): name for name in rows_by_entity}
        relationships: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for entity_name, rows in rows_by_entity.items():
            if not rows:
                continue
            sample_keys = {k for row in rows[:5] for k in row.keys()}
            for key in sample_keys:
                lowered = str(key).lower()
                if lowered in ("id", "_id") or not lowered.endswith("_id"):
                    continue
                candidate = lowered[: -len("_id")]
                target = entity_names.get(_singularize(candidate)) or entity_names.get(candidate)
                if not target or target == entity_name:
                    continue
                signature = (entity_name, key, target)
                if signature in seen:
                    continue
                seen.add(signature)
                relationships.append(
                    {"from_entity": entity_name, "field": key, "likely_target_entity": target}
                )

        return relationships

    # --- findings --------------------------------------------------------

    def _derive_findings(
        self, entities: list[ConnectorEntitySummary], relationships: list[dict[str, Any]]
    ) -> list[Finding]:
        findings: list[Finding] = []

        for entity in entities:
            if not entity.reachable or not entity.row_count:
                continue
            s = entity.summary

            if entity.kind == "invoice":
                severity = "warning" if s.get("overdue_count", 0) > 0 else "info"
                findings.append(
                    Finding(
                        id=f"connector-{entity.entity}-invoices",
                        kind="connector",
                        severity=severity,
                        title=f"{entity.entity}: {s.get('paid_count', 0)} paid / {s.get('unpaid_count', 0)} unpaid",
                        message=(
                            f"Your connected '{entity.entity}' data reports {s.get('paid_amount', 0)} paid and "
                            f"{s.get('unpaid_amount', 0)} outstanding across {s.get('row_count', 0)} record(s)"
                            + (f", including {s.get('overdue_count', 0)} overdue." if s.get("overdue_count", 0) else ".")
                        ),
                        data=s,
                    )
                )
            elif entity.kind == "inventory" and s.get("low_stock_count", 0) > 0:
                findings.append(
                    Finding(
                        id=f"connector-{entity.entity}-low-stock",
                        kind="connector",
                        severity="warning",
                        title=f"{entity.entity}: {s['low_stock_count']} item(s) low on stock",
                        message="Items at or below "
                        f"{_LOW_STOCK_THRESHOLD} units: "
                        + ", ".join(f"{it['item']} ({it['quantity']})" for it in s["low_stock_items"][:3])
                        + ("..." if s["low_stock_count"] > 3 else ""),
                        data=s,
                    )
                )
            elif entity.kind == "employee":
                findings.append(
                    Finding(
                        id=f"connector-{entity.entity}-headcount",
                        kind="connector",
                        severity="info",
                        title=f"{entity.entity}: {s.get('active_count', entity.row_count)} active record(s)",
                        message=f"Your connected '{entity.entity}' data reports {entity.row_count} record(s)"
                        + (f", {s.get('inactive_count', 0)} marked inactive." if s.get("inactive_count", 0) else "."),
                        data=s,
                    )
                )
            elif entity.kind == "payment":
                findings.append(
                    Finding(
                        id=f"connector-{entity.entity}-payments",
                        kind="connector",
                        severity="info",
                        title=f"{entity.entity}: {entity.row_count} record(s) synced",
                        message=f"Totalling {s.get('total_amount', 0)} across {s.get('known_amount_rows', 0)} "
                        "record(s) with a recognized amount field.",
                        data=s,
                    )
                )
            elif entity.kind == "generic" and s.get("total_amount") is not None:
                findings.append(
                    Finding(
                        id=f"connector-{entity.entity}-generic",
                        kind="connector",
                        severity="info",
                        title=f"{entity.entity}: {entity.row_count} record(s), {s['total_amount']} total",
                        message=f"Orbit couldn't confidently classify '{entity.entity}', but it carries a "
                        f"recognizable amount field ('{s.get('amount_field')}') worth {s['total_amount']} total.",
                        data=s,
                    )
                )

        unreachable = [e for e in entities if not e.reachable and e.error]
        if unreachable and any(e.reachable for e in entities):
            findings.append(
                Finding(
                    id="connector-partial",
                    kind="connector",
                    severity="info",
                    title=f"{len(unreachable)} connector entit(y/ies) not returning data",
                    message="Orbit could not read "
                    + ", ".join(e.entity for e in unreachable)
                    + " from your connector - check the entity is still mapped and the connector file is deployed.",
                    data={"entities": [e.entity for e in unreachable]},
                )
            )

        if relationships:
            findings.append(
                Finding(
                    id="connector-relationships",
                    kind="connector",
                    severity="info",
                    title=f"{len(relationships)} link(s) found between your connected tables",
                    message="; ".join(
                        f"{r['from_entity']}.{r['field']} \u2192 {r['likely_target_entity']}" for r in relationships[:5]
                    )
                    + ("..." if len(relationships) > 5 else ""),
                    data={"relationships": relationships},
                )
            )

        return findings
