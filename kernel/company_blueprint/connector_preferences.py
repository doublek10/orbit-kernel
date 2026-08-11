"""
Connector Generator preferences

Small companion store to connector_generator.py / connector_tester.py.
Those two stay stateless on purpose (see their docstrings) - this
module is the one place that remembers anything, and it only
remembers what's safe to: the language ("code extension" - javascript/
php/python/java), the database engine, and a deployed Connector URL
the company pasted in after deploying their generated file.

Same non-negotiable as the generator itself: host, port, database
name, username, and above all the password are NEVER written here.
Only language + database + connector_url are persisted - one row per
company, upserted every time the wizard is used.
"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class ConnectorPreferences:
    language: str
    database: str
    connector_url: str | None
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "database": self.database,
            "connector_url": self.connector_url,
            "updated_at": self.updated_at,
        }


class ConnectorPreferencesStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get(self, company_id: str) -> ConnectorPreferences | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM connector_preferences WHERE company_id = $1", company_id
            )
        return self._row(row) if row else None

    async def save(
        self,
        company_id: str,
        language: str,
        database: str,
        connector_url: str | None,
    ) -> ConnectorPreferences:
        """
        Upserts the one row this company gets. connector_url is stored
        exactly as given - an empty/blank value is normalized to NULL
        so "remembered but empty" and "never set" read the same way.
        """
        clean_url = (connector_url or "").strip() or None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO connector_preferences (company_id, language, database_engine, connector_url)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (company_id) DO UPDATE
                SET language = EXCLUDED.language,
                    database_engine = EXCLUDED.database_engine,
                    connector_url = EXCLUDED.connector_url,
                    updated_at = now()
                RETURNING *
                """,
                company_id,
                language,
                database,
                clean_url,
            )
        return self._row(row)

    async def delete(self, company_id: str) -> bool:
        """
        Forgets this company's saved settings entirely. Returns True if
        a row was actually removed, False if there was nothing saved
        to begin with - either way the wizard starts fresh next time.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM connector_preferences WHERE company_id = $1", company_id
            )
        return result.endswith("1")

    @staticmethod
    def _row(row) -> ConnectorPreferences:
        return ConnectorPreferences(
            language=row["language"],
            database=row["database_engine"],
            connector_url=row["connector_url"],
            updated_at=row["updated_at"].isoformat(),
        )