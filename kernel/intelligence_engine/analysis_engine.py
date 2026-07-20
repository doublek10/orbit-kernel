"""
Intelligence Engine - Analysis Engine

Continuous evaluation of revenue, cash flow, spend concentration, and
anomalies (spec's "Continuous Analysis" list - the rest of that list,
inventory/payroll/supplier performance, activates once a connected
Business System actually produces that data; nothing here fabricates
numbers for systems that aren't connected).

Deliberately transparent statistics, not a model call - same rule
ai/insights.py already followed, and the same "explain your reasoning"
requirement the spec's Deterministic Intelligence section demands: given
the same Blueprint, Country Package, and ledger data, this always
produces the same Findings.

`allowed_categories` (from the Blueprint - see
kernel/company_blueprint/validator.py's Blueprint Governance fields)
restricts which ledger categories this module is allowed to name in a
Finding: None means unrestricted, a list means "only these". This is
the spec's "Allowed Entities" / "Available Fields" made real - a
category outside the list is invisible to spend/anomaly analysis, the
same way an unregistered API is invisible to the Engine entirely (spec's
Authorized Communication section). Overall net cash flow (`_flow_trend`)
is deliberately NOT restricted - it describes the whole business, not a
specific entity, the same way `balance_summary` isn't restricted either.
"""

import asyncpg

from kernel.intelligence_engine.models import Finding


class AnalysisEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def analyze(self, company_id: str, allowed_categories: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []

        trend = await self._flow_trend(company_id)
        if trend is not None:
            findings.append(trend)

        category = await self._top_outflow_category(company_id, allowed_categories)
        if category is not None:
            findings.append(category)

        anomalies = await self._anomaly_finding(company_id, allowed_categories)
        if anomalies is not None:
            findings.append(anomalies)

        return findings

    async def _flow_trend(self, company_id: str) -> Finding | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'inflow' AND occurred_at >= now() - interval '30 days'), 0)
                        - COALESCE(SUM(amount) FILTER (WHERE direction = 'outflow' AND occurred_at >= now() - interval '30 days'), 0)
                        AS net_current,
                    COALESCE(SUM(amount) FILTER (WHERE direction = 'inflow' AND occurred_at >= now() - interval '60 days' AND occurred_at < now() - interval '30 days'), 0)
                        - COALESCE(SUM(amount) FILTER (WHERE direction = 'outflow' AND occurred_at >= now() - interval '60 days' AND occurred_at < now() - interval '30 days'), 0)
                        AS net_previous
                FROM ledger_transactions
                WHERE company_id = $1
                """,
                company_id,
            )
        current, previous = float(row["net_current"]), float(row["net_previous"])
        if current == 0 and previous == 0:
            return None

        change_pct = 100.0 if previous == 0 and current > 0 else -100.0 if previous == 0 else ((current - previous) / abs(previous)) * 100
        direction = "improved" if change_pct >= 0 else "declined"
        return Finding(
            id="flow-trend",
            kind="trend",
            severity="info" if change_pct >= 0 else "warning",
            title=f"Net cash flow {direction} {abs(round(change_pct))}% vs. the prior 30 days",
            message=f"Net flow was {round(current, 2)} this month vs {round(previous, 2)} last month.",
            data={"current_net": round(current, 2), "previous_net": round(previous, 2), "change_pct": round(change_pct, 1)},
        )

    async def _top_outflow_category(self, company_id: str, allowed_categories: list[str] | None) -> Finding | None:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT category, SUM(amount) AS total
                FROM ledger_transactions
                WHERE company_id = $1 AND direction = 'outflow'
                  AND occurred_at >= now() - interval '30 days'
                  AND ($2::text[] IS NULL OR category = ANY($2::text[]))
                GROUP BY category
                ORDER BY total DESC
                LIMIT 1
                """,
                company_id,
                allowed_categories,
            )
            if not rows:
                return None
            total_out = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount), 0) FROM ledger_transactions
                WHERE company_id = $1 AND direction = 'outflow' AND occurred_at >= now() - interval '30 days'
                  AND ($2::text[] IS NULL OR category = ANY($2::text[]))
                """,
                company_id,
                allowed_categories,
            )
        row = rows[0]
        share = (float(row["total"]) / float(total_out) * 100) if total_out else 0
        return Finding(
            id="top-category",
            kind="spend",
            severity="info",
            title=f"{row['category'].title()} is your largest spend category",
            message=f"{round(share)}% of outflow over the last 30 days ({round(float(row['total']), 2)}).",
            data={"category": row["category"], "amount": round(float(row["total"]), 2), "share_pct": round(share, 1)},
        )

    async def _anomaly_finding(self, company_id: str, allowed_categories: list[str] | None) -> Finding | None:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT description, counterparty, amount, occurred_at
                FROM ledger_transactions
                WHERE company_id = $1 AND is_anomaly
                  AND occurred_at >= now() - interval '30 days'
                  AND ($2::text[] IS NULL OR category = ANY($2::text[]))
                ORDER BY occurred_at DESC
                LIMIT 5
                """,
                company_id,
                allowed_categories,
            )
        if not rows:
            return None
        return Finding(
            id="anomalies",
            kind="anomaly",
            severity="warning",
            title=f"{len(rows)} unusual transaction(s) flagged for review",
            message=", ".join(r["counterparty"] or r["description"] or "Unknown" for r in rows[:3]),
            data={
                "transactions": [
                    {
                        "description": r["counterparty"] or r["description"],
                        "amount": float(r["amount"]),
                        "occurred_at": r["occurred_at"].isoformat(),
                    }
                    for r in rows
                ]
            },
        )
