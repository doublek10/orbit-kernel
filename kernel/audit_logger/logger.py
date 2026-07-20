"""
Audit Logger

Every action the Kernel takes on behalf of a user is recorded. This is not
optional or configurable per-workflow - Development Rule #8 in the Kernel
README: "Every action is audited."
"""


import asyncpg


class AuditLogger:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def record(
        self,
        *,
        actor_id: str,
        company_id: str | None,
        action: str,
        metadata: dict | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (actor_id, company_id, action, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                actor_id,
                company_id,
                action,
                metadata or {},
            )

    async def list_events(self, company_id: str, limit: int = 25) -> list[dict]:
        """Most recent actions first, actor resolved to an email for
        display - backs the Security page's activity feed."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT al.action, al.metadata, al.created_at, u.email AS actor_email
                FROM audit_log al
                LEFT JOIN users u ON u.id = al.actor_id
                WHERE al.company_id = $1
                ORDER BY al.created_at DESC
                LIMIT $2
                """,
                company_id,
                limit,
            )
        return [
            {
                "action": row["action"],
                "metadata": row["metadata"],
                "actor_email": row["actor_email"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
