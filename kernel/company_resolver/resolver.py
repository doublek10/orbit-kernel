"""
Company Resolver

Every workflow begins with company resolution. Given a verified user id,
this determines which company (tenant) the request operates within, which
Postgres data belongs to that tenant, and which country package governs it.

If a user belongs to more than one company, the caller (Gateway, on behalf
of the frontend) must supply a company_id to disambiguate. If they belong
to exactly one, it's resolved automatically.
"""

from dataclasses import dataclass

import asyncpg
from fastapi import HTTPException, status


@dataclass(frozen=True)
class ResolvedCompany:
    id: str
    name: str
    country: str


class CompanyResolver:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def resolve(self, user_id: str, company_id: str | None) -> ResolvedCompany:
        async with self._pool.acquire() as conn:
            if company_id:
                row = await conn.fetchrow(
                    """
                    SELECT c.id, c.name, c.country
                    FROM companies c
                    JOIN company_members m ON m.company_id = c.id
                    WHERE m.user_id = $1 AND c.id = $2
                    """,
                    user_id,
                    company_id,
                )
                if row is None:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        "User is not a member of the requested company",
                    )
                return ResolvedCompany(row["id"], row["name"], row["country"])

            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.country
                FROM companies c
                JOIN company_members m ON m.company_id = c.id
                WHERE m.user_id = $1
                ORDER BY m.created_at ASC
                """,
                user_id,
            )
            if not rows:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "User does not belong to any company",
                )
            if len(rows) > 1:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "User belongs to multiple companies - company_id is required",
                )
            row = rows[0]
            return ResolvedCompany(row["id"], row["name"], row["country"])
