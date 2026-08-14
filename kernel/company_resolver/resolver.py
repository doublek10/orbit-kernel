"""
Company Resolver

Every workflow begins with company resolution. Given a verified user id,
this determines which company (tenant) the request operates within, which
Postgres data belongs to that tenant, and which country package governs it.

If a user belongs to more than one company, the caller (Gateway, on behalf
of the frontend) must supply a company_id to disambiguate. If they belong
to exactly one, it's resolved automatically.

Also enforces the Admin Control Panel's deactivation switches
(`companies.is_active`, `users.is_active`) AND subscription expiry
(`company_subscriptions`): this is the one place every single
authenticated request passes through on its way to a workflow, so it's
the correct place to make "deactivate a company", "deactivate a user",
or "let a company's subscription lapse" actually take effect
immediately, on the very next request - not just at their next login.

Subscription enforcement is opt-in per company: a company with no rows
in `company_subscriptions` at all is never blocked for it (see
kernel/admin/subscriptions.py) - only a company an admin has explicitly
granted a subscription to can ever be blocked for letting it expire.
"""

from dataclasses import dataclass

import asyncpg
from fastapi import HTTPException, status

from kernel.admin.subscriptions import SubscriptionManager


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
            user_row = await conn.fetchrow(
                "SELECT is_active FROM users WHERE id = $1", user_id
            )
            if user_row is not None and not user_row["is_active"]:
                await self._alert_deactivated_access("user", user_id, None)
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "This account has been deactivated by the platform administrator",
                )

            if company_id:
                row = await conn.fetchrow(
                    """
                    SELECT c.id, c.name, c.country, c.is_active
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
                if not row["is_active"]:
                    await self._alert_deactivated_access("company", user_id, row["id"])
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        "This company has been deactivated by the platform administrator",
                    )
                await self._enforce_subscription(conn, user_id, row["id"])
                return ResolvedCompany(row["id"], row["name"], row["country"])

            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.country, c.is_active
                FROM companies c
                JOIN company_members m ON m.company_id = c.id
                WHERE m.user_id = $1
                ORDER BY m.created_at ASC
                """,
                user_id,
            )
            active_rows = [r for r in rows if r["is_active"]]
            if not active_rows:
                if rows:
                    await self._alert_deactivated_access("company", user_id, rows[0]["id"])
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        "This company has been deactivated by the platform administrator",
                    )
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "User does not belong to any company",
                )
            if len(active_rows) > 1:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "User belongs to multiple companies - company_id is required",
                )
            row = active_rows[0]
            await self._enforce_subscription(conn, user_id, row["id"])
            return ResolvedCompany(row["id"], row["name"], row["country"])

    async def _enforce_subscription(
        self, conn: asyncpg.Connection, user_id: str, company_id: str
    ) -> None:
        sub_row = await conn.fetchrow(
            """
            SELECT status, ends_at FROM company_subscriptions
            WHERE company_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            company_id,
        )
        if not SubscriptionManager.is_blocked(sub_row):
            return

        await self._alert_deactivated_access("company_subscription", user_id, company_id)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This company's subscription has expired or been cancelled",
        )

    async def _alert_deactivated_access(
        self, kind: str, user_id: str, company_id: str | None
    ) -> None:
        try:
            from kernel.admin.security_alerts import SecurityAlerts

            await SecurityAlerts(self._pool).record(
                severity="warning",
                category=f"deactivated_{kind}_access_attempt",
                message=f"A request was made using a deactivated {kind} (user_id={user_id}).",
                company_id=company_id,
            )
        except Exception:
            pass
