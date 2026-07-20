"""
Intelligence Engine - Manager

The front door described in the spec's "Intelligence Manager" section:
start/stop the Engine per company, load its context, and run one
Intelligence Cycle end to end. Every other entry point into the engine -
the Observer reacting to an event, the Scheduler running a due job, or
the Workflow Engine answering a Frontend read - goes through an
IntelligenceManager instance rather than calling analysis_engine /
report_generator / etc. directly, so "no user directly controls the
Intelligence Engine" (Intelligence Rule #1) has exactly one gate to
enforce it at: `is_active()`, checked before every cycle runs.
"""

import asyncpg

from kernel.event_bus.bus import get_event_bus
from kernel.intelligence_engine import cache_manager
from kernel.intelligence_engine.context_builder import ContextBuilder
from kernel.intelligence_engine.knowledge_graph import KnowledgeGraph
from kernel.intelligence_engine.metrics import MetricsStore
from kernel.intelligence_engine.models import ReasoningResult
from kernel.intelligence_engine.notification_engine import NotificationEngine
from kernel.intelligence_engine.reasoning_engine import ReasoningEngine
from kernel.intelligence_engine.recommendation_engine import RecommendationEngine
from kernel.intelligence_engine.report_generator import ReportGenerator

_DEFAULT_PREFERENCES = {
    "daily_summary": True,
    "weekly_executive": True,
    "monthly_forecast": True,
    "min_notification_severity": "info",
}


class IntelligenceManager:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._context = ContextBuilder(pool)
        self._reasoning = ReasoningEngine(pool)
        self._knowledge = KnowledgeGraph(pool)
        self._metrics = MetricsStore(pool)
        self._recommendations = RecommendationEngine(pool)
        self._notifications = NotificationEngine(pool)
        self._reports = ReportGenerator(pool)
        self._events = get_event_bus(pool)

    # --- lifecycle (spec: Intelligence Lifecycle / Rules #1-4) ----------

    async def activate(self, company_id: str, blueprint_version: int | None = None) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO intelligence_status (company_id, active, activated_at, blueprint_version)
                    VALUES ($1, true, now(), $2)
                    ON CONFLICT (company_id) DO UPDATE SET
                        active = true,
                        activated_at = COALESCE(intelligence_status.activated_at, now()),
                        deactivated_at = NULL,
                        blueprint_version = EXCLUDED.blueprint_version
                    """,
                    company_id,
                    blueprint_version,
                )
                await conn.execute(
                    """
                    INSERT INTO intelligence_preferences (company_id)
                    VALUES ($1)
                    ON CONFLICT (company_id) DO NOTHING
                    """,
                    company_id,
                )
        cache_manager.invalidate(company_id)

    async def deactivate(self, company_id: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE intelligence_status
                SET active = false, deactivated_at = now()
                WHERE company_id = $1
                """,
                company_id,
            )
        cache_manager.invalidate(company_id)

    async def is_active(self, company_id: str) -> bool:
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT active FROM intelligence_status WHERE company_id = $1", company_id
            )
        return bool(value)

    async def get_status(self, company_id: str) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM intelligence_status WHERE company_id = $1", company_id
            )
        if row is None:
            return {
                "company_id": company_id,
                "active": False,
                "activated_at": None,
                "deactivated_at": None,
                "blueprint_version": None,
                "last_event_at": None,
                "last_cycle_at": None,
            }
        return {
            "company_id": company_id,
            "active": row["active"],
            "activated_at": row["activated_at"].isoformat() if row["activated_at"] else None,
            "deactivated_at": row["deactivated_at"].isoformat() if row["deactivated_at"] else None,
            "blueprint_version": row["blueprint_version"],
            "last_event_at": row["last_event_at"].isoformat() if row["last_event_at"] else None,
            "last_cycle_at": row["last_cycle_at"].isoformat() if row["last_cycle_at"] else None,
        }

    # --- the Intelligence Cycle (spec: Event Processing Flow) -----------

    async def run_cycle(self, company_id: str, *, trigger: str = "manual") -> ReasoningResult | None:
        if not await self.is_active(company_id):
            return None

        # "Load Company Context" / "Load Blueprint" - not consumed by
        # the deterministic statistics below yet (analysis_engine /
        # forecasting_engine don't branch on business_type today), but
        # every cycle resolves it, both to keep the lifecycle step real
        # per the spec and so a future business-type-aware Analysis
        # Engine has it available without a signature change here.
        await self._context.build(company_id)

        result = await self._reasoning.run(company_id)

        allowed_categories = (result.blueprint or {}).get("allowed_categories")
        await self._knowledge.rebuild(company_id, allowed_categories)
        await self._metrics.record(company_id, "health_score", result.health["score"], {"label": result.health["label"]})
        await self._metrics.record(company_id, "net_cash_flow_30d", result.summary["net_30d"])
        await self._metrics.record(company_id, "balance", result.summary["balance"])
        await self._recommendations.generate_and_store(result)
        await self._notifications.notify(result)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE intelligence_status
                SET last_cycle_at = now(),
                    last_event_at = CASE WHEN $2 != 'scheduled' THEN now() ELSE last_event_at END
                WHERE company_id = $1
                """,
                company_id,
                trigger,
            )

        cache_manager.invalidate(company_id)
        await self._events.publish(
            "intelligence.cycle_completed",
            {"trigger": trigger, "health_score": result.health["score"]},
            company_id=company_id,
        )
        return result

    async def on_event(self, event_name: str, payload: dict, company_id: str | None) -> None:
        """Called by the Observer for every subscribed event."""
        if company_id is None:
            return
        if event_name == "blueprint.published":
            await self.activate(company_id, blueprint_version=payload.get("version"))
            return
        await self.run_cycle(company_id, trigger=event_name)

    # --- reads the Workflow Engine / Gateway expose ----------------------

    async def get_dashboard(self, company_id: str) -> dict:
        async def compute() -> dict:
            status = await self.get_status(company_id)
            result = await self._reasoning.run(company_id)
            unread = await self._unread_notification_count(company_id)
            open_recs = await self._open_recommendation_count(company_id)
            return {
                "status": status,
                "summary": result.summary,
                "health": result.health,
                "findings": [f.to_dict() for f in result.findings],
                "forecast": result.forecast,
                "unread_notifications": unread,
                "open_recommendations": open_recs,
            }

        return await cache_manager.get_or_compute(f"{company_id}:dashboard", compute)

    async def get_reports(self, company_id: str, report_type: str | None = None, limit: int = 20) -> dict:
        return {"reports": await self._reports.list_reports(company_id, report_type=report_type, limit=limit)}

    async def generate_report(self, company_id: str, report_type: str) -> dict:
        result = await self._reasoning.run(company_id)
        return await self._reports.generate(result, report_type)

    async def get_notifications(self, company_id: str, unread_only: bool = False, limit: int = 50) -> dict:
        async with self._pool.acquire() as conn:
            if unread_only:
                rows = await conn.fetch(
                    """
                    SELECT id, category, severity, title, message, data, created_at, read_at
                    FROM intelligence_notifications
                    WHERE company_id = $1 AND read_at IS NULL
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    company_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, category, severity, title, message, data, created_at, read_at
                    FROM intelligence_notifications
                    WHERE company_id = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    company_id,
                    limit,
                )
        return {
            "notifications": [
                {
                    "id": str(r["id"]),
                    "category": r["category"],
                    "severity": r["severity"],
                    "title": r["title"],
                    "message": r["message"],
                    "data": r["data"],
                    "created_at": r["created_at"].isoformat(),
                    "read_at": r["read_at"].isoformat() if r["read_at"] else None,
                }
                for r in rows
            ]
        }

    async def mark_notification_read(self, company_id: str, notification_id: str) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE intelligence_notifications SET read_at = now()
                WHERE id = $1 AND company_id = $2 AND read_at IS NULL
                RETURNING id
                """,
                notification_id,
                company_id,
            )
        return row is not None

    async def get_forecast(self, company_id: str) -> dict:
        result = await self._reasoning.run(company_id)
        return result.forecast

    async def get_performance(self, company_id: str) -> dict:
        result = await self._reasoning.run(company_id)
        latest_metrics = await self._metrics.all_latest(company_id)
        return {
            "summary": result.summary,
            "findings": [f.to_dict() for f in result.findings],
            "metrics": {k: v.to_dict() for k, v in latest_metrics.items()},
        }

    async def get_knowledge(self, company_id: str) -> dict:
        return await self._knowledge.read(company_id)

    async def get_history(self, company_id: str, metric_key: str, limit: int = 90) -> dict:
        points = await self._metrics.history(company_id, metric_key, limit=limit)
        return {"metric_key": metric_key, "points": [p.to_dict() for p in points]}

    async def get_preferences(self, company_id: str) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM intelligence_preferences WHERE company_id = $1", company_id
            )
        if row is None:
            return {"company_id": company_id, **_DEFAULT_PREFERENCES}
        return {
            "company_id": company_id,
            "daily_summary": row["daily_summary"],
            "weekly_executive": row["weekly_executive"],
            "monthly_forecast": row["monthly_forecast"],
            "min_notification_severity": row["min_notification_severity"],
        }

    async def set_preferences(self, company_id: str, payload: dict) -> dict:
        severity = payload.get("min_notification_severity", "info")
        if severity not in ("info", "warning", "critical"):
            raise ValueError("min_notification_severity must be one of: info, warning, critical")

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO intelligence_preferences
                    (company_id, daily_summary, weekly_executive, monthly_forecast, min_notification_severity, updated_at)
                VALUES ($1, $2, $3, $4, $5, now())
                ON CONFLICT (company_id) DO UPDATE SET
                    daily_summary = EXCLUDED.daily_summary,
                    weekly_executive = EXCLUDED.weekly_executive,
                    monthly_forecast = EXCLUDED.monthly_forecast,
                    min_notification_severity = EXCLUDED.min_notification_severity,
                    updated_at = now()
                """,
                company_id,
                bool(payload.get("daily_summary", True)),
                bool(payload.get("weekly_executive", True)),
                bool(payload.get("monthly_forecast", True)),
                severity,
            )
        return await self.get_preferences(company_id)

    async def _unread_notification_count(self, company_id: str) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM intelligence_notifications WHERE company_id = $1 AND read_at IS NULL",
                company_id,
            )

    async def _open_recommendation_count(self, company_id: str) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM intelligence_recommendations WHERE company_id = $1 AND dismissed_at IS NULL",
                company_id,
            )


_manager: IntelligenceManager | None = None


def get_intelligence_manager(pool: asyncpg.Pool) -> IntelligenceManager:
    """Process-wide singleton, same pattern as get_provider_manager() -
    the Observer and Scheduler need one standing instance to call into,
    not a fresh one per request."""
    global _manager
    if _manager is None:
        _manager = IntelligenceManager(pool)
    return _manager
