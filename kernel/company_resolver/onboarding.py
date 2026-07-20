"""
Onboarding

This is the concrete "Kernel uses the Supabase UUID to create the rest in
Postgres" step. Runs as a single DB transaction: if any part fails, none
of it is committed - we never want a Supabase user to exist without a
matching company/membership row, or vice versa.
"""

from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class OnboardedCompany:
    user_id: str
    email: str
    company_id: str
    company_name: str
    country: str
    role: str


async def create_company_and_owner(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    email: str,
    full_name: str | None,
    company_name: str,
    country: str,
) -> OnboardedCompany:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO users (id, email, full_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO NOTHING
                """,
                user_id,
                email,
                full_name,
            )

            company_row = await conn.fetchrow(
                """
                INSERT INTO companies (name, country)
                VALUES ($1, $2)
                RETURNING id, name, country
                """,
                company_name,
                country,
            )

            await conn.execute(
                """
                INSERT INTO company_members (user_id, company_id, role, permissions)
                VALUES ($1, $2, 'owner', '["*"]'::jsonb)
                """,
                user_id,
                company_row["id"],
            )

    return OnboardedCompany(
        user_id=user_id,
        email=email,
        company_id=str(company_row["id"]),
        company_name=company_row["name"],
        country=company_row["country"],
        role="owner",
    )
