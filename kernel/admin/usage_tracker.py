"""
Usage Tracker

Records a lightweight event on every Kernel `/execute` call, classified
as read / write / analysis by the workflow's name, so the Admin Control
Panel can show each company's data-flow mix at a glance - e.g.
"Company 1: 15% read, 16% write, 27% analysis". This is intentionally a
simple, count-based approximation (not a byte-level profiler): the goal
is an operator-facing signal, not a billing meter.

Classification is a naming convention, not a hardcoded workflow list, so
it keeps working as new workflows are added to the Workflow Engine
without this file needing a matching update every time.
"""

import datetime

import asyncpg

WRITE_PREFIXES = (
    "create", "update", "delete", "set", "rotate", "connect", "disconnect",
    "restore", "generate", "sign", "revoke", "deactivate", "activate",
    "import", "publish", "compile", "restore", "test",
)
ANALYSIS_PREFIXES = (
    "analytics", "replay", "forecast", "insight", "report", "graph",
    "intelligence", "performance", "ai", "knowledge",
)


def classify(workflow: str) -> str:
    """companies.list -> read, companies.create -> write,
    analytics.dashboard -> analysis. Falls back to 'read' - the safest
    default for anything that doesn't match a known verb, since most
    Kernel workflows are reads."""
    name = workflow.lower()
    head = name.split(".", 1)[0]

    if head in ANALYSIS_PREFIXES or any(name.startswith(p) for p in ANALYSIS_PREFIXES):
        return "analysis"
    if any(head.startswith(p) or name.startswith(p) for p in WRITE_PREFIXES):
        return "write"
    return "read"


class UsageTracker:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def record(self, company_id: str | None, workflow: str) -> None:
        if not company_id:
            return
        event_type = classify(workflow)
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO company_usage_events (company_id, event_type, workflow)
                    VALUES ($1, $2, $3)
                    """,
                    company_id,
                    event_type,
                    workflow,
                )
        except Exception:
            # Usage tracking is observability, never allowed to break a
            # real tenant request.
            pass

    async def summary(self, since_hours: int = 24) -> list[dict]:
        """One row per company: read/write/analysis percentages over the
        trailing window, plus its active/deactivated flag. Backs the
        Admin Overview page."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.country, c.is_active,
                       count(e.*) FILTER (WHERE e.event_type = 'read') AS reads,
                       count(e.*) FILTER (WHERE e.event_type = 'write') AS writes,
                       count(e.*) FILTER (WHERE e.event_type = 'analysis') AS analysis,
                       count(e.*) AS total,
                       s.status AS sub_status, s.ends_at AS sub_ends_at,
                       s.amount_cents AS sub_amount_cents, s.currency AS sub_currency
                FROM companies c
                LEFT JOIN company_usage_events e
                    ON e.company_id = c.id
                   AND e.created_at > now() - ($1 || ' hours')::interval
                LEFT JOIN LATERAL (
                    SELECT status, ends_at, amount_cents, currency
                    FROM company_subscriptions
                    WHERE company_id = c.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) s ON true
                GROUP BY c.id, c.name, c.country, c.is_active,
                         s.status, s.ends_at, s.amount_cents, s.currency
                ORDER BY total DESC, c.name ASC
                """,
                str(since_hours),
            )

        def pct(part: int, total: int) -> float:
            return round((part / total) * 100, 1) if total else 0.0

        def subscription_status(sub_status: str | None, ends_at) -> str:
            if sub_status is None:
                return "none"
            if sub_status == "cancelled":
                return "cancelled"
            if ends_at < datetime.datetime.now(datetime.timezone.utc):
                return "expired"
            return "active"

        return [
            {
                "company_id": str(r["id"]),
                "name": r["name"],
                "country": r["country"],
                "is_active": r["is_active"],
                "read_pct": pct(r["reads"], r["total"]),
                "write_pct": pct(r["writes"], r["total"]),
                "analysis_pct": pct(r["analysis"], r["total"]),
                "total_events": r["total"],
                "window_hours": since_hours,
                "subscription_status": subscription_status(r["sub_status"], r["sub_ends_at"]),
                "subscription_ends_at": r["sub_ends_at"].isoformat() if r["sub_ends_at"] else None,
                "subscription_amount_display": (
                    f"{r['sub_amount_cents'] / 100:.2f} {r['sub_currency']}"
                    if r["sub_amount_cents"] is not None
                    else None
                ),
            }
            for r in rows
        ]
