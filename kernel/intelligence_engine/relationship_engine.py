"""
Intelligence Engine - Relationship Engine

Figures out which entities are connected and how strongly, from the one
authorized data source the engine is allowed to read today: the
Financial Graph (spec: "Authorized Communication" - it may only read
Registered Entities/Relationships, never scan or guess). Retail,
services, and every other business type currently produce the same
shape of relationships here (category <-> account, counterparty <->
category) because ledger_transactions is the only Business System wired
up yet; a connected payroll or inventory system would add its own entity
types without changing how this module is called.
"""

from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class Relationship:
    from_type: str
    from_key: str
    relationship: str
    to_type: str
    to_key: str
    weight: float


class RelationshipEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def derive(self, company_id: str, allowed_categories: list[str] | None = None) -> list[Relationship]:
        relationships: list[Relationship] = []

        async with self._pool.acquire() as conn:
            category_rows = await conn.fetch(
                """
                SELECT category, direction, SUM(amount) AS total
                FROM ledger_transactions
                WHERE company_id = $1 AND occurred_at >= now() - interval '90 days'
                  AND ($2::text[] IS NULL OR category = ANY($2::text[]))
                GROUP BY category, direction
                """,
                company_id,
                allowed_categories,
            )
            counterparty_rows = await conn.fetch(
                """
                SELECT category, counterparty, SUM(amount) AS total
                FROM ledger_transactions
                WHERE company_id = $1 AND counterparty IS NOT NULL
                  AND occurred_at >= now() - interval '90 days'
                  AND ($2::text[] IS NULL OR category = ANY($2::text[]))
                GROUP BY category, counterparty
                ORDER BY total DESC
                LIMIT 25
                """,
                company_id,
                allowed_categories,
            )

        for row in category_rows:
            relationship = "flows_into" if row["direction"] == "inflow" else "flows_from"
            relationships.append(
                Relationship("category", row["category"], relationship, "account", "primary", float(row["total"]))
            )

        for row in counterparty_rows:
            relationships.append(
                Relationship(
                    "counterparty", row["counterparty"], "contributes_to", "category", row["category"], float(row["total"])
                )
            )

        return relationships
