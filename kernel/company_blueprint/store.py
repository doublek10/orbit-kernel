"""
Company Blueprint (store)

The smallest real slice of the full Company Blueprint spec: what a
company owner tells Orbit on first login about how they want the system
to behave. Two workflows only:

    blueprint.list    -> current blueprint + whether onboarding is done
    blueprint.create  -> publish a new version (upsert + immutable history)

Everything else in the full spec (financial connections, business
systems, schema builder, SDK generator) already has its own home
(provider_manager, etc.) or is a later build-out - this module only owns
the "how do you want Orbit to work" preferences and their version
history, per Design Principle #5 ("every Blueprint change is versioned").
"""

from dataclasses import dataclass
from typing import Any

import asyncpg


VALID_PRIORITIES = {
    "cash_flow_visibility",
    "expense_control",
    "payroll_accuracy",
    "fraud_and_risk_alerts",
    "growth_forecasting",
}


@dataclass(frozen=True)
class Blueprint:
    company_id: str
    business_type: str
    priorities: list[str]
    large_transaction_threshold: float | None
    notify_on_large_transaction: bool
    weekly_digest: bool
    version: int
    published_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_type": self.business_type,
            "priorities": self.priorities,
            "large_transaction_threshold": self.large_transaction_threshold,
            "notify_on_large_transaction": self.notify_on_large_transaction,
            "weekly_digest": self.weekly_digest,
            "version": self.version,
            "published_at": self.published_at,
        }


class BlueprintStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get(self, company_id: str) -> Blueprint | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM company_blueprints WHERE company_id = $1", company_id
            )
        if row is None:
            return None
        return self._row_to_blueprint(row)

    async def publish(
        self,
        *,
        company_id: str,
        published_by: str,
        business_type: str,
        priorities: list[str],
        large_transaction_threshold: float | None,
        notify_on_large_transaction: bool,
        weekly_digest: bool,
    ) -> Blueprint:
        business_type = (business_type or "").strip()
        if not business_type:
            raise ValueError("business_type is required")

        clean_priorities = [p for p in priorities if p in VALID_PRIORITIES]

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO company_blueprints
                        (company_id, business_type, priorities, large_transaction_threshold,
                         notify_on_large_transaction, weekly_digest, version, published_by,
                         published_at, updated_at)
                    VALUES ($1, $2, $3::jsonb, $4, $5, $6, 1, $7, now(), now())
                    ON CONFLICT (company_id) DO UPDATE SET
                        business_type = EXCLUDED.business_type,
                        priorities = EXCLUDED.priorities,
                        large_transaction_threshold = EXCLUDED.large_transaction_threshold,
                        notify_on_large_transaction = EXCLUDED.notify_on_large_transaction,
                        weekly_digest = EXCLUDED.weekly_digest,
                        version = company_blueprints.version + 1,
                        published_by = EXCLUDED.published_by,
                        published_at = now(),
                        updated_at = now()
                    RETURNING *
                    """,
                    company_id,
                    business_type,
                    clean_priorities,
                    large_transaction_threshold,
                    notify_on_large_transaction,
                    weekly_digest,
                    published_by,
                )

                blueprint = self._row_to_blueprint(row)

                await conn.execute(
                    """
                    INSERT INTO company_blueprint_versions
                        (company_id, version, snapshot, published_by)
                    VALUES ($1, $2, $3::jsonb, $4)
                    """,
                    company_id,
                    blueprint.version,
                    _to_jsonb(blueprint.to_dict()),
                    published_by,
                )

        return blueprint

    @staticmethod
    def _row_to_blueprint(row) -> Blueprint:
        import json

        priorities = row["priorities"]
        if isinstance(priorities, str):
            priorities = json.loads(priorities)

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
            version=row["version"],
            published_at=row["published_at"].isoformat(),
        )


def _to_jsonb(payload: dict) -> str:
    import json

    return json.dumps(payload)
