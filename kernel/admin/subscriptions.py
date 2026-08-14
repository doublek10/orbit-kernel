"""
Subscriptions

A company subscription is a simple one-month billing period an admin
can grant once a company is active - "the subscription starts that day
and ends same time the other month". No plans, no payment processing:
just a start and an end timestamp, a fixed price for display purposes
only, a derived status, and who granted it.

Deliberately opt-in per company: a company with no subscription rows at
all is not gated by subscription status (see the enforcement in
kernel/company_resolver/resolver.py). Only a company an admin has
explicitly granted at least one subscription to can ever be blocked for
being expired - this lets the feature be adopted gradually.
"""

from __future__ import annotations

import datetime

import asyncpg

# Every company is currently charged the same fixed amount - there is
# still no payment processing anywhere in this system. This is a
# stored, displayed figure only (what the subscription is *worth*, for
# the admin to see and for future invoicing/billing work to read from),
# never an actual charge against a card or bank account. Stored as
# integer cents to avoid floating-point rounding on money.
SUBSCRIPTION_AMOUNT_CENTS = 15000  # $150.00
SUBSCRIPTION_CURRENCY = "USD"


class SubscriptionError(Exception):
    """Raised for any subscription-grant failure the API layer should
    surface as a 400, e.g. granting to a company that isn't active."""


class SubscriptionManager:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def grant(self, company_id: str, granted_by: str) -> dict:
        """Starts a new one-month period from right now, at the fixed
        platform price. Calling this again before the current period
        ends simply starts a fresh month from today, rather than
        stacking on top of the old end date - an explicit "renew now"
        action, not silent accumulation."""
        async with self._pool.acquire() as conn:
            company = await conn.fetchrow(
                "SELECT is_active FROM companies WHERE id = $1", company_id
            )
            if company is None:
                raise SubscriptionError("Company not found")
            if not company["is_active"]:
                raise SubscriptionError(
                    "Company must be activated before it can be given a subscription"
                )

            row = await conn.fetchrow(
                """
                INSERT INTO company_subscriptions
                    (company_id, started_at, ends_at, granted_by, amount_cents, currency)
                VALUES ($1, now(), now() + interval '1 month', $2, $3, $4)
                RETURNING id, company_id, status, started_at, ends_at, created_at,
                          amount_cents, currency
                """,
                company_id,
                granted_by,
                SUBSCRIPTION_AMOUNT_CENTS,
                SUBSCRIPTION_CURRENCY,
            )
        return self._row(row)

    async def cancel(self, company_id: str) -> None:
        """Ends the current period early. Does nothing (silently) if
        the company has no subscription at all - cancelling something
        that was never granted isn't an error."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE company_subscriptions SET status = 'cancelled'
                WHERE id = (
                    SELECT id FROM company_subscriptions
                    WHERE company_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                """,
                company_id,
            )

    async def current(self, company_id: str) -> dict | None:
        """The most recent subscription period for a company, or None
        if it has never been granted one at all - distinct from
        'expired', which means it HAD one and it lapsed."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, company_id, status, started_at, ends_at, created_at,
                       amount_cents, currency
                FROM company_subscriptions
                WHERE company_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                company_id,
            )
        return self._row(row) if row else None

    @staticmethod
    def is_blocked(row: asyncpg.Record | None) -> bool:
        """Used by company_resolver.py on the raw DB row (not the
        serialized dict) to decide whether to 403 a request. A company
        with no row at all (row is None) is never blocked."""
        if row is None:
            return False
        if row["status"] == "cancelled":
            return True
        return row["ends_at"] < datetime.datetime.now(datetime.timezone.utc)

    @staticmethod
    def _row(row: asyncpg.Record) -> dict:
        ends_at = row["ends_at"]
        if row["status"] == "cancelled":
            effective_status = "cancelled"
        elif ends_at < datetime.datetime.now(datetime.timezone.utc):
            effective_status = "expired"
        else:
            effective_status = "active"

        return {
            "id": row["id"],
            "company_id": str(row["company_id"]),
            "status": effective_status,
            "started_at": row["started_at"].isoformat(),
            "ends_at": ends_at.isoformat(),
            "created_at": row["created_at"].isoformat(),
            "amount_cents": row["amount_cents"],
            "currency": row["currency"],
            # Convenience field so callers (Admin Gateway/Frontend)
            # don't each need their own cents-to-dollars formatting
            # logic just to show "$150.00".
            "amount_display": f"{row['amount_cents'] / 100:.2f} {row['currency']}",
        }
