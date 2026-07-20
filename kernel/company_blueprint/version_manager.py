"""
Version Manager

Every Blueprint modification creates a new, immutable version - never an
in-place edit of history (Design Principle #5). This module owns that
contract for the Company Blueprint specifically:

    publish()        - validated payload -> new active Blueprint (version N+1)
    list_versions()  - full history, newest first
    get_version()    - one immutable snapshot
    restore()        - re-publish an old snapshot as a NEW version (the
                        old version itself is never touched or deleted)
    compare()         - field-level diff between two versions

Nothing here decides who is *allowed* to call these (that's Ownership,
enforced one layer up in the Workflow Engine) - this module only
guarantees that whatever gets published is valid and durably recorded.
"""

import json
from dataclasses import dataclass
from typing import Any

import asyncpg

from kernel.company_blueprint.validator import validate_blueprint_input


@dataclass(frozen=True)
class Blueprint:
    company_id: str
    business_type: str
    priorities: list[str]
    large_transaction_threshold: float | None
    notify_on_large_transaction: bool
    weekly_digest: bool
    enabled_capabilities: list[str]
    allowed_categories: list[str] | None
    version: int
    published_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_type": self.business_type,
            "priorities": self.priorities,
            "large_transaction_threshold": self.large_transaction_threshold,
            "notify_on_large_transaction": self.notify_on_large_transaction,
            "weekly_digest": self.weekly_digest,
            "enabled_capabilities": self.enabled_capabilities,
            "allowed_categories": self.allowed_categories,
            "version": self.version,
            "published_at": self.published_at,
        }


def row_to_blueprint(row) -> Blueprint:
    priorities = row["priorities"]
    if isinstance(priorities, str):
        priorities = json.loads(priorities)

    enabled_capabilities = row["enabled_capabilities"]
    if isinstance(enabled_capabilities, str):
        enabled_capabilities = json.loads(enabled_capabilities)

    allowed_categories = row["allowed_categories"]
    if isinstance(allowed_categories, str):
        allowed_categories = json.loads(allowed_categories)

    return Blueprint(
        company_id=str(row["company_id"]),
        business_type=row["business_type"],
        priorities=list(priorities or []),
        large_transaction_threshold=(
            float(row["large_transaction_threshold"])
            if row["large_transaction_threshold"] is not None
            else None
        ),
        notify_on_large_transaction=row["notify_on_large_transaction"],
        weekly_digest=row["weekly_digest"],
        enabled_capabilities=list(enabled_capabilities or []),
        allowed_categories=list(allowed_categories) if allowed_categories else None,
        version=row["version"],
        published_at=row["published_at"].isoformat(),
    )


class VersionManager:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def publish(self, *, company_id: str, published_by: str, payload: dict) -> Blueprint:
        """Validates, upserts the active row (version = version + 1), and
        writes an immutable snapshot in the same transaction - a
        Blueprint publish is atomic, never partially applied."""
        clean = validate_blueprint_input(payload)

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO company_blueprints
                        (company_id, business_type, priorities, large_transaction_threshold,
                         notify_on_large_transaction, weekly_digest, enabled_capabilities,
                         allowed_categories, version, published_by, published_at, updated_at)
                    VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7::jsonb, $8::jsonb, 1, $9, now(), now())
                    ON CONFLICT (company_id) DO UPDATE SET
                        business_type = EXCLUDED.business_type,
                        priorities = EXCLUDED.priorities,
                        large_transaction_threshold = EXCLUDED.large_transaction_threshold,
                        notify_on_large_transaction = EXCLUDED.notify_on_large_transaction,
                        weekly_digest = EXCLUDED.weekly_digest,
                        enabled_capabilities = EXCLUDED.enabled_capabilities,
                        allowed_categories = EXCLUDED.allowed_categories,
                        version = company_blueprints.version + 1,
                        published_by = EXCLUDED.published_by,
                        published_at = now(),
                        updated_at = now()
                    RETURNING *
                    """,
                    company_id,
                    clean["business_type"],
                    clean["priorities"],
                    clean["large_transaction_threshold"],
                    clean["notify_on_large_transaction"],
                    clean["weekly_digest"],
                    clean["enabled_capabilities"],
                    clean["allowed_categories"],
                    published_by,
                )
                blueprint = row_to_blueprint(row)

                await conn.execute(
                    """
                    INSERT INTO company_blueprint_versions (company_id, version, snapshot, published_by)
                    VALUES ($1, $2, $3::jsonb, $4)
                    """,
                    company_id,
                    blueprint.version,
                    blueprint.to_dict(),
                    published_by,
                )

        return blueprint

    async def get_active(self, company_id: str) -> Blueprint | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM company_blueprints WHERE company_id = $1", company_id
            )
        return row_to_blueprint(row) if row else None

    async def list_versions(self, company_id: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT cbv.version, cbv.snapshot, cbv.created_at, u.email AS published_by_email
                FROM company_blueprint_versions cbv
                JOIN users u ON u.id = cbv.published_by
                WHERE cbv.company_id = $1
                ORDER BY cbv.version DESC
                """,
                company_id,
            )
        return [
            {
                "version": row["version"],
                "snapshot": json.loads(row["snapshot"])
                if isinstance(row["snapshot"], str)
                else row["snapshot"],
                "published_by_email": row["published_by_email"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    async def get_version(self, company_id: str, version: int) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT version, snapshot, created_at
                FROM company_blueprint_versions
                WHERE company_id = $1 AND version = $2
                """,
                company_id,
                version,
            )
        if row is None:
            return None
        snapshot = row["snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        return {"version": row["version"], "snapshot": snapshot, "created_at": row["created_at"].isoformat()}

    async def restore(self, *, company_id: str, published_by: str, version: int) -> Blueprint:
        """Re-publishes an old snapshot as a brand-new version. The
        snapshot being restored FROM is never modified or deleted - this
        only ever adds to history, consistent with every other publish."""
        old = await self.get_version(company_id, version)
        if old is None:
            raise ValueError(f"Blueprint version {version} does not exist")
        snapshot = old["snapshot"]
        return await self.publish(
            company_id=company_id,
            published_by=published_by,
            payload={
                "business_type": snapshot["business_type"],
                "priorities": snapshot["priorities"],
                "large_transaction_threshold": snapshot["large_transaction_threshold"],
                "notify_on_large_transaction": snapshot["notify_on_large_transaction"],
                "weekly_digest": snapshot["weekly_digest"],
                # Older snapshots (published before Blueprint Governance
                # existed) won't have these keys - fall back to
                # validate_blueprint_input's own defaults (all
                # capabilities, unrestricted categories) rather than
                # KeyError on a legitimate restore.
                "enabled_capabilities": snapshot.get("enabled_capabilities"),
                "allowed_categories": snapshot.get("allowed_categories"),
            },
        )

    async def compare(self, company_id: str, version_a: int, version_b: int) -> dict:
        a = await self.get_version(company_id, version_a)
        b = await self.get_version(company_id, version_b)
        if a is None or b is None:
            raise ValueError("Both versions must exist to compare")

        fields = [
            "business_type",
            "priorities",
            "large_transaction_threshold",
            "notify_on_large_transaction",
            "weekly_digest",
        ]
        diff = []
        for field in fields:
            va, vb = a["snapshot"].get(field), b["snapshot"].get(field)
            if va != vb:
                diff.append({"field": field, "from": va, "to": vb})

        return {
            "from_version": version_a,
            "to_version": version_b,
            "changed": diff,
            "identical": len(diff) == 0,
        }
