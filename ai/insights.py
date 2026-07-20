"""
AI Insights

Per this module's own design rule: AI never performs business actions -
it only analyzes, predicts, scores, and recommends. The Workflow Engine
(and ultimately the person looking at the dashboard) decides whether a
recommendation becomes an action, e.g. by creating a Workflow automation.

This first version is intentionally a transparent statistical engine,
not a call to an external LLM - there's no model provider wired up yet,
and "explain your reasoning" is much easier to guarantee with arithmetic
over the Financial Graph than with a prompted model. Swap or augment
individual insight generators with real model calls later; the shape
callers receive (a list of {type, severity, title, message, data})
doesn't need to change for that.
"""

from datetime import datetime, timezone

import asyncpg

from financial_graph.graph import FinancialGraph


class AIInsights:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._graph = FinancialGraph(pool)

    async def generate(self, company_id: str) -> list[dict]:
        insights: list[dict] = []

        summary = await self._graph.balance_summary(company_id)
        health = await self._graph.health_score(company_id)
        insights.append(self._health_insight(health, summary))

        trend = await self._flow_trend(company_id)
        if trend is not None:
            insights.append(trend)

        category = await self._top_outflow_category(company_id)
        if category is not None:
            insights.append(category)

        anomalies = await self._anomaly_insight(company_id)
        if anomalies is not None:
            insights.append(anomalies)

        forecast = self._forecast_insight(summary)
        insights.append(forecast)

        return insights

    def _health_insight(self, health: dict, summary: dict) -> dict:
        severity = {"strong": "info", "watch": "warning", "at risk": "critical"}[health["label"]]
        return {
            "id": "health-score",
            "type": "health",
            "severity": severity,
            "title": f"Business health: {health['label']} ({health['score']}/100)",
            "message": health["signals"][0] if health["signals"] else "",
            "data": {"score": health["score"], "signals": health["signals"], "summary": summary},
        }

    async def _flow_trend(self, company_id: str) -> dict | None:
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

        if previous == 0:
            change_pct = 100.0 if current > 0 else -100.0
        else:
            change_pct = ((current - previous) / abs(previous)) * 100

        direction = "improved" if change_pct >= 0 else "declined"
        return {
            "id": "flow-trend",
            "type": "trend",
            "severity": "info" if change_pct >= 0 else "warning",
            "title": f"Net cash flow {direction} {abs(round(change_pct))}% vs. the prior 30 days",
            "message": f"Net flow was {round(current, 2)} this month vs {round(previous, 2)} last month.",
            "data": {"current_net": round(current, 2), "previous_net": round(previous, 2)},
        }

    async def _top_outflow_category(self, company_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT category, SUM(amount) AS total
                FROM ledger_transactions
                WHERE company_id = $1 AND direction = 'outflow'
                  AND occurred_at >= now() - interval '30 days'
                GROUP BY category
                ORDER BY total DESC
                LIMIT 1
                """,
                company_id,
            )
        if not rows:
            return None
        row = rows[0]
        async with self._pool.acquire() as conn:
            total_out = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount), 0) FROM ledger_transactions
                WHERE company_id = $1 AND direction = 'outflow' AND occurred_at >= now() - interval '30 days'
                """,
                company_id,
            )
        share = (float(row["total"]) / float(total_out) * 100) if total_out else 0
        return {
            "id": "top-category",
            "type": "spend",
            "severity": "info",
            "title": f"{row['category'].title()} is your largest spend category",
            "message": f"{round(share)}% of outflow over the last 30 days ({round(float(row['total']), 2)}).",
            "data": {"category": row["category"], "amount": round(float(row["total"]), 2), "share_pct": round(share, 1)},
        }

    async def _anomaly_insight(self, company_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT description, counterparty, amount, occurred_at
                FROM ledger_transactions
                WHERE company_id = $1 AND is_anomaly
                ORDER BY occurred_at DESC
                LIMIT 5
                """,
                company_id,
            )
        if not rows:
            return None
        return {
            "id": "anomalies",
            "type": "anomaly",
            "severity": "warning",
            "title": f"{len(rows)} unusual transaction(s) flagged for review",
            "message": ", ".join(r["counterparty"] or r["description"] or "Unknown" for r in rows[:3]),
            "data": {
                "transactions": [
                    {
                        "description": r["counterparty"] or r["description"],
                        "amount": float(r["amount"]),
                        "occurred_at": r["occurred_at"].isoformat(),
                    }
                    for r in rows
                ]
            },
        }

    def _forecast_insight(self, summary: dict) -> dict:
        daily_net = summary["net_30d"] / 30 if summary["net_30d"] else 0
        projected_30d = round(summary["balance"] + daily_net * 30, 2)
        severity = "critical" if projected_30d < 0 else "info"
        return {
            "id": "forecast-30d",
            "type": "forecast",
            "severity": severity,
            "title": f"Projected balance in 30 days: {projected_30d}",
            "message": "Based on your current 30-day average net cash flow, held constant. "
            + ("This goes negative - review upcoming spend." if projected_30d < 0 else "Trajectory looks stable."),
            "data": {"projected_balance_30d": projected_30d, "daily_net_avg": round(daily_net, 2)},
        }
