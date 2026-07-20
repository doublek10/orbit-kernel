"""
Feature Flags (stub)

Per-company / per-plan feature toggles, read from Postgres. Not yet wired
to a table - add a `feature_flags` table and back this with a real query
when the first flag is needed.
"""


class FeatureFlags:
    async def is_enabled(self, company_id: str, flag: str) -> bool:
        return False
