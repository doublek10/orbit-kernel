"""
Permission Engine

Determines what an identity is allowed to do within a resolved company:
role, feature permissions, marketplace permissions, enterprise permissions.
Nothing downstream (Rule Engine, Workflow Engine) executes before this runs.

Permissions are stored as a JSON grant list per company membership so new
capabilities (marketplace apps, enterprise features) can be added without
schema changes.
"""

from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class ResolvedPermissions:
    role: str
    grants: list[str]


class PermissionEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def resolve(self, user_id: str, company_id: str) -> ResolvedPermissions:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT role, permissions
                FROM company_members
                WHERE user_id = $1 AND company_id = $2
                """,
                user_id,
                company_id,
            )
            if row is None:
                return ResolvedPermissions(role="none", grants=[])

            grants = row["permissions"] or []
            # Owners implicitly hold every grant; everyone else gets exactly
            # what's stored against their membership.
            if row["role"] == "owner" and "*" not in grants:
                grants = [*grants, "*"]

            return ResolvedPermissions(role=row["role"], grants=grants)
