"""
Blueprint Loader

Loads the ACTIVE Company Blueprint for a company and hands back the
piece of context every other Kernel module (Rule Engine, Workflow
Engine, later the Transformation Engine) should read it from - "builds
an execution context" per the spec, kept intentionally small here since
the rest of the ExecutionContext lives in kernel/context.py.

Cached per-process, per-company. Invalidated the instant a new version
is published (see VersionManager.publish, called by the Workflow
Engine's blueprint.create/blueprint.restore handlers) - nothing
downstream re-reads Postgres for a Blueprint that hasn't changed.
"""

import asyncpg

from kernel.company_blueprint.version_manager import Blueprint, row_to_blueprint

_cache: dict[str, Blueprint] = {}


class BlueprintLoader:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def load(self, company_id: str) -> Blueprint | None:
        if company_id in _cache:
            return _cache[company_id]

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM company_blueprints WHERE company_id = $1", company_id
            )
        if row is None:
            return None

        blueprint = row_to_blueprint(row)
        _cache[company_id] = blueprint
        return blueprint

    @staticmethod
    def invalidate(company_id: str) -> None:
        _cache.pop(company_id, None)
