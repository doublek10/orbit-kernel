"""
Intelligence Engine - Context Builder

Every user-triggered Kernel action reads its ExecutionContext from
kernel/context.py, built from a Supabase token. Background Intelligence
work has no token and no user - it runs because an event fired or a
scheduled job came due - so it needs its own, smaller context: which
company, which Blueprint, which Country Package. This is that "builds an
execution context" step from the spec's lifecycle, scoped to what the
engine actually needs.
"""

from dataclasses import dataclass

import asyncpg

from country_packages.registry import get_country_package
from kernel.company_blueprint.version_manager import Blueprint
from kernel.company_blueprint.loader import BlueprintLoader


@dataclass(frozen=True)
class IntelligenceContext:
    company_id: str
    country: str
    currency: str
    blueprint: Blueprint | None

    @property
    def priorities(self) -> list[str]:
        return list(self.blueprint.priorities) if self.blueprint else []

    @property
    def business_type(self) -> str | None:
        return self.blueprint.business_type if self.blueprint else None


class ContextBuilder:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._blueprints = BlueprintLoader(pool)

    async def build(self, company_id: str) -> IntelligenceContext:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT country FROM companies WHERE id = $1", company_id)
        country = row["country"] if row and row["country"] else "KE"

        blueprint = await self._blueprints.load(company_id)
        country_pkg = get_country_package(country)

        return IntelligenceContext(
            company_id=company_id,
            country=country,
            currency=country_pkg.currency,
            blueprint=blueprint,
        )
