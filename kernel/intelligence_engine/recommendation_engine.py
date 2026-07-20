"""
Intelligence Engine - Recommendation Engine

Turns a ReasoningResult into advice, never an action (spec: "MAY
Recommend" / "MUST NEVER ... Perform Workflow Actions"). Whether a
recommendation becomes an automation is entirely up to the person
looking at it, via workflows.create - same boundary ai/insights.py
already documented for the older, request-scoped insights endpoint.

Recommendations are deduped per rec_type over a 24h window so a
still-true fact doesn't spam a new row every single cycle - the Notifi-
cation Engine (separate module) already carries the "tell someone now"
job; this store is closer to a standing to-do list than an alert feed.
"""

import asyncpg

from kernel.intelligence_engine.models import ReasoningResult


class RecommendationEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def generate_and_store(self, result: ReasoningResult) -> list[dict]:
        candidates = self._derive(result)
        stored = []
        async with self._pool.acquire() as conn:
            for rec_type, title, message, data in candidates:
                existing = await conn.fetchval(
                    """
                    SELECT id FROM intelligence_recommendations
                    WHERE company_id = $1 AND rec_type = $2
                      AND created_at >= now() - interval '24 hours'
                      AND dismissed_at IS NULL
                    LIMIT 1
                    """,
                    result.company_id,
                    rec_type,
                )
                if existing:
                    continue
                row = await conn.fetchrow(
                    """
                    INSERT INTO intelligence_recommendations (company_id, rec_type, title, message, data)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    RETURNING id, created_at
                    """,
                    result.company_id,
                    rec_type,
                    title,
                    message,
                    data,
                )
                stored.append({"id": str(row["id"]), "rec_type": rec_type, "title": title, "message": message, "data": data})
        return stored

    def _derive(self, result: ReasoningResult) -> list[tuple[str, str, str, dict]]:
        candidates: list[tuple[str, str, str, dict]] = []

        if result.summary["net_30d"] < 0:
            top_spend = next((f for f in result.findings if f.id == "top-category"), None)
            if top_spend is not None:
                candidates.append(
                    (
                        "reduce_top_outflow",
                        f"Consider trimming {top_spend.data['category']} spend",
                        f"Net cash flow is negative and {top_spend.data['category']} is your largest outflow "
                        f"category ({top_spend.data['share_pct']}% of spend) - it's the highest-leverage place to cut.",
                        {"category": top_spend.data["category"]},
                    )
                )

        anomalies = next((f for f in result.findings if f.id == "anomalies"), None)
        if anomalies is not None:
            candidates.append(
                (
                    "review_anomalies",
                    "Review flagged transactions",
                    anomalies.message,
                    anomalies.data,
                )
            )

        if result.forecast["projected_balance"]["30d"] < 0:
            candidates.append(
                (
                    "address_forecast_shortfall",
                    "Projected shortfall within 30 days",
                    "At the current run rate, balance is projected to go negative within 30 days. "
                    "Consider slowing outflow or lining up additional inflow.",
                    result.forecast,
                )
            )

        return candidates
