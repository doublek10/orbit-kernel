"""
Database adapter for the Kernel's self-hosted Postgres instance.

This is the ONLY database the Kernel talks to. Supabase is never queried
here for anything except, indirectly, JWT verification (which doesn't even
require a network call - see shared/auth/supabase_jwt.py).

The connection string should point at a Postgres instance reachable only
over the private network / VPN, never a public endpoint.
"""

import json

import asyncpg
from shared.config import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    # Without this, jsonb/json columns come back as raw strings instead
    # of dicts/lists - every module that reads a jsonb column (Permission
    # Engine, Workflow Automation, Event Bus, ...) relies on this running.
    await conn.set_type_codec(
        "jsonb", encoder=lambda v: json.dumps(v, default=str), decoder=json.loads, schema="pg_catalog", format="text"
    )
    await conn.set_type_codec(
        "json", encoder=lambda v: json.dumps(v, default=str), decoder=json.loads, schema="pg_catalog", format="text"
    )


async def connect() -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.database_pool_min,
            max_size=settings.database_pool_max,
            init=_init_connection,
        )
    return _pool


async def disconnect() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised - did startup run?")
    return _pool
