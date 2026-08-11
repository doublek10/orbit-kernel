"""
Connector Tester (Test Connection)

Runs a live, read-only preview against a company's own database using
the connection details and table map they entered in the Connector
Generator wizard. This module never writes to Orbit's own Postgres and
never logs a password - it exists purely to answer "can Orbit reach my
system, and does what it sees look right", the same job
_company_test_endpoint does for the webhook mechanism in
workflow_engine/engine.py. Nothing it returns is saved anywhere; call
it again and it reads fresh, live data straight from the socket.

Same honesty contract as providers.test / integrations.test elsewhere
in this Engine: where a real driver is installed on this Kernel we
attempt a genuine connection; where it isn't, we say so plainly
instead of fabricating a "connected: true".

Two ways to reach a company's data:
  - Direct: connection has host/port/database/username(/password) and
    this Kernel opens a socket straight to their database. Needs the
    database to be network-reachable from wherever the Kernel runs.
  - Via URL: connection has a connector_url - the live address of a
    file the company generated with the Connector Generator and
    deployed on their own hosting (see connector_generator.py's HTTP
    entrypoints). The Kernel never touches the database directly here;
    it just calls that URL with ?entity=<name>&limit=<n> and reads
    back the JSON the deployed file returns. This is the path for
    companies on shared hosting where the database itself isn't
    reachable but a plain URL is.
connector_url always wins when both are present, since the whole point
of pasting one is "call this instead of connecting directly".
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlparse

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAMPLE_ROWS = 3
_CONNECT_TIMEOUT = 6
_OVERALL_TIMEOUT = 20
_MAX_FIELD_CHARS = 200


def _safe_identifier(name: str) -> str | None:
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        return None
    return name


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_FIELD_CHARS:
        return value[:_MAX_FIELD_CHARS] + "…"
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return value


def _clean_tables(tables: list[dict] | None) -> list[dict]:
    cleaned = []
    for t in tables or []:
        if not isinstance(t, dict):
            continue
        entity = str(t.get("entity") or "table").strip() or "table"
        table = str(t.get("table") or "").strip()
        cleaned.append({"entity": entity, "table": table})
    return cleaned


def _empty_table_result(entity: str, table: str, error: str) -> dict:
    return {
        "entity": entity,
        "table": table,
        "reachable": False,
        "columns": [],
        "row_count": None,
        "sample_rows": [],
        "error": error,
    }


def _fail(database: str, message: str) -> dict:
    return {
        "database": database,
        "connected": False,
        "error": message,
        "tables": [],
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "saved": False,
    }


async def test_connection(database: str, connection: dict | None, tables: list[dict] | None) -> dict:
    """
    Attempts a real, read-only connection and previews up to 3 sample
    rows per requested table/collection, plus a best-effort row count.
    Always returns a result (never raises) - failures show up as
    connected: False / a per-table error, matching how the rest of the
    Test Connection surfaces already behave.
    """
    connection = connection or {}
    tables = _clean_tables(tables)
    if not tables:
        return _fail(database, "Add at least one table so Orbit knows what to look at.")

    connector_url = str(connection.get("connector_url") or "").strip()
    if connector_url:
        try:
            result = await asyncio.wait_for(
                _test_via_url(connector_url, connection.get("connector_token"), tables),
                timeout=_OVERALL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return _fail(
                database,
                "Timed out - Orbit couldn't reach your connector URL in time. Check that it's "
                "deployed, publicly reachable, and responding to ?entity=... requests.",
            )
        except Exception as exc:  # last-resort honesty net - never crash the request
            return _fail(database, f"Could not reach connector URL: {exc}")

        result["database"] = database
        result["tested_at"] = datetime.now(timezone.utc).isoformat()
        result["saved"] = False
        return result

    host = str(connection.get("host") or "").strip()
    if not host:
        return _fail(
            database,
            "A host (or file path, for SQLite) is required to test the connection - or paste "
            "a Connector URL above if Orbit should call your deployed connector file instead.",
        )

    handler = _HANDLERS.get(database)
    if handler is None:
        return _fail(database, f"Unsupported database '{database}'.")

    try:
        result = await asyncio.wait_for(handler(connection, tables), timeout=_OVERALL_TIMEOUT)
    except asyncio.TimeoutError:
        return _fail(
            database,
            "Timed out - Orbit couldn't reach your database in time. Check the host/port, "
            "and that it's reachable from where Orbit runs.",
        )
    except Exception as exc:  # last-resort honesty net - never crash the request
        return _fail(database, f"Could not connect: {exc}")

    result["database"] = database
    result["tested_at"] = datetime.now(timezone.utc).isoformat()
    result["saved"] = False
    return result


# --- Via a pasted Connector URL --------------------------------------------
# The counterpart to the HTTP entrypoints connector_generator.py adds to
# every generated file: instead of Orbit opening a socket to the
# company's database, it calls the URL the company pasted into the
# wizard once they deployed their connector file, and reads back JSON.
# connector_token is optional and only sent if the company set one -
# open (no token) is the default on both sides, per the generator's
# ORBIT_CONNECTOR_TOKEN block, which they can turn on themselves.

_ALLOWED_URL_SCHEMES = {"http", "https"}


async def _test_via_url(connector_url: str, connector_token: Any, tables: list[dict]) -> dict:
    parsed = urlparse(connector_url)
    if parsed.scheme not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        return {"connected": False, "error": "Connector URL must be a full http(s):// address.", "tables": []}

    headers = {}
    if connector_token:
        headers["X-Orbit-Token"] = str(connector_token)

    import httpx

    async with httpx.AsyncClient(timeout=_CONNECT_TIMEOUT, headers=headers) as client:
        try:
            health = await client.get(connector_url, params={"entity": "_health"})
        except httpx.HTTPError as exc:
            return {"connected": False, "error": f"Could not reach the connector URL: {exc}", "tables": []}

        if health.status_code == 401:
            return {"connected": False, "error": "Connector URL rejected the request (401) - check the token.", "tables": []}
        if health.status_code >= 400:
            return {"connected": False, "error": f"Connector URL returned HTTP {health.status_code}.", "tables": []}

        results = []
        for entry in tables:
            results.append(await _url_table_preview(client, connector_url, entry))
        return {"connected": True, "error": None, "tables": results}


async def _url_table_preview(client, connector_url: str, entry: dict) -> dict:
    entity, table = entry["entity"], entry["table"]
    try:
        res = await client.get(connector_url, params={"entity": entity, "limit": _SAMPLE_ROWS})
    except Exception as exc:
        return _empty_table_result(entity, table, str(exc))

    if res.status_code >= 400:
        try:
            body = res.json()
            message = body.get("error") or f"HTTP {res.status_code}"
        except Exception:
            message = f"HTTP {res.status_code}"
        return _empty_table_result(entity, table, message)

    try:
        body = res.json()
    except Exception:
        return _empty_table_result(entity, table, "Connector URL did not return valid JSON.")

    if not body.get("ok", True):
        return _empty_table_result(entity, table, body.get("error") or "Connector reported an error.")

    rows = body.get("rows") or []
    columns = sorted({k for row in rows if isinstance(row, dict) for k in row.keys()})
    return {
        "entity": entity,
        "table": table,
        "reachable": True,
        "columns": columns,
        "row_count": len(rows) if isinstance(rows, list) else None,
        "sample_rows": [
            {k: _truncate(v) for k, v in row.items()} if isinstance(row, dict) else row
            for row in rows[:_SAMPLE_ROWS]
        ],
        "error": None,
    }


# --- PostgreSQL ----------------------------------------------------------

async def _test_postgresql(connection: dict, tables: list[dict]) -> dict:
    try:
        import asyncpg
    except ImportError:
        return {"connected": False, "error": "asyncpg is not installed on this Kernel.", "tables": []}

    try:
        conn = await asyncpg.connect(
            host=connection.get("host"),
            port=int(connection.get("port") or 5432),
            database=connection.get("database"),
            user=connection.get("username"),
            password=connection.get("password"),
            ssl="require" if connection.get("ssl") else None,
            timeout=_CONNECT_TIMEOUT,
        )
    except Exception as exc:
        return {"connected": False, "error": str(exc), "tables": []}

    results = []
    try:
        for entry in tables:
            results.append(await _pg_table_preview(conn, entry))
    finally:
        await conn.close()
    return {"connected": True, "error": None, "tables": results}


async def _pg_table_preview(conn, entry: dict) -> dict:
    entity, table = entry["entity"], entry["table"]
    safe_table = _safe_identifier(table)
    if not safe_table:
        return _empty_table_result(entity, table, "Not a valid table name")
    try:
        rows = await conn.fetch(f'SELECT * FROM "{safe_table}" LIMIT {_SAMPLE_ROWS}')
        count_row = await conn.fetchrow(f'SELECT COUNT(*) AS n FROM "{safe_table}"')
        columns = list(rows[0].keys()) if rows else [
            r["column_name"]
            for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = $1 ORDER BY ordinal_position",
                safe_table,
            )
        ]
        return {
            "entity": entity,
            "table": table,
            "reachable": True,
            "columns": columns,
            "row_count": count_row["n"] if count_row else None,
            "sample_rows": [{k: _truncate(v) for k, v in dict(r).items()} for r in rows],
            "error": None,
        }
    except Exception as exc:
        return _empty_table_result(entity, table, str(exc))


# --- MySQL -----------------------------------------------------------------

async def _test_mysql(connection: dict, tables: list[dict]) -> dict:
    try:
        import aiomysql
    except ImportError:
        return {
            "connected": False,
            "error": "aiomysql is not installed on this Kernel (pip install aiomysql).",
            "tables": [],
        }

    try:
        conn = await asyncio.wait_for(
            aiomysql.connect(
                host=connection.get("host"),
                port=int(connection.get("port") or 3306),
                db=connection.get("database"),
                user=connection.get("username"),
                password=connection.get("password"),
                ssl=True if connection.get("ssl") else None,
                connect_timeout=_CONNECT_TIMEOUT,
            ),
            timeout=_CONNECT_TIMEOUT,
        )
    except Exception as exc:
        return {"connected": False, "error": str(exc), "tables": []}

    results = []
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            for entry in tables:
                results.append(await _mysql_table_preview(cur, entry))
    finally:
        conn.close()
    return {"connected": True, "error": None, "tables": results}


async def _mysql_table_preview(cur, entry: dict) -> dict:
    entity, table = entry["entity"], entry["table"]
    safe_table = _safe_identifier(table)
    if not safe_table:
        return _empty_table_result(entity, table, "Not a valid table name")
    try:
        await cur.execute(f"SELECT * FROM `{safe_table}` LIMIT {_SAMPLE_ROWS}")
        rows = await cur.fetchall()
        await cur.execute(f"SELECT COUNT(*) AS n FROM `{safe_table}`")
        count_row = await cur.fetchone()
        columns = list(rows[0].keys()) if rows else []
        if not columns:
            await cur.execute(f"SHOW COLUMNS FROM `{safe_table}`")
            columns = [r["Field"] for r in await cur.fetchall()]
        return {
            "entity": entity,
            "table": table,
            "reachable": True,
            "columns": columns,
            "row_count": count_row["n"] if count_row else None,
            "sample_rows": [{k: _truncate(v) for k, v in r.items()} for r in rows],
            "error": None,
        }
    except Exception as exc:
        return _empty_table_result(entity, table, str(exc))


# --- MongoDB ---------------------------------------------------------------

async def _test_mongodb(connection: dict, tables: list[dict]) -> dict:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        return {
            "connected": False,
            "error": "motor is not installed on this Kernel (pip install motor).",
            "tables": [],
        }

    host = connection.get("host")
    port = int(connection.get("port") or 27017)
    user = connection.get("username")
    password = connection.get("password")
    database = connection.get("database") or "admin"
    auth = f"{user}:{password}@" if user else ""
    uri = f"mongodb://{auth}{host}:{port}/{database}"
    if connection.get("ssl"):
        uri += "?tls=true"

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=_CONNECT_TIMEOUT * 1000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        client.close()
        return {"connected": False, "error": str(exc), "tables": []}

    db = client[database]
    results = []
    for entry in tables:
        results.append(await _mongo_collection_preview(db, entry))
    client.close()
    return {"connected": True, "error": None, "tables": results}


async def _mongo_collection_preview(db, entry: dict) -> dict:
    entity, collection_name = entry["entity"], entry["table"]
    if not collection_name:
        return _empty_table_result(entity, collection_name, "No collection name given")
    try:
        collection = db[collection_name]
        docs = await collection.find().limit(_SAMPLE_ROWS).to_list(length=_SAMPLE_ROWS)
        count = await collection.estimated_document_count()
        columns = sorted({k for d in docs for k in d.keys()})
        sample_rows = [
            {k: _truncate(str(v) if k == "_id" else v) for k, v in d.items()} for d in docs
        ]
        return {
            "entity": entity,
            "table": collection_name,
            "reachable": True,
            "columns": columns,
            "row_count": count,
            "sample_rows": sample_rows,
            "error": None,
        }
    except Exception as exc:
        return _empty_table_result(entity, collection_name, str(exc))


# --- SQLite ------------------------------------------------------------

async def _test_sqlite(connection: dict, tables: list[dict]) -> dict:
    try:
        import aiosqlite
    except ImportError:
        return {
            "connected": False,
            "error": "aiosqlite is not installed on this Kernel (pip install aiosqlite).",
            "tables": [],
        }

    path = connection.get("database") or connection.get("host")
    if not path:
        return {"connected": False, "error": "Provide the .sqlite/.db file path.", "tables": []}

    try:
        conn = await asyncio.wait_for(aiosqlite.connect(path), timeout=_CONNECT_TIMEOUT)
        conn.row_factory = aiosqlite.Row
    except Exception as exc:
        return {"connected": False, "error": str(exc), "tables": []}

    results = []
    try:
        for entry in tables:
            results.append(await _sqlite_table_preview(conn, entry))
    finally:
        await conn.close()
    return {"connected": True, "error": None, "tables": results}


async def _sqlite_table_preview(conn, entry: dict) -> dict:
    entity, table = entry["entity"], entry["table"]
    safe_table = _safe_identifier(table)
    if not safe_table:
        return _empty_table_result(entity, table, "Not a valid table name")
    try:
        cur = await conn.execute(f'SELECT * FROM "{safe_table}" LIMIT {_SAMPLE_ROWS}')
        rows = await cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        count_cur = await conn.execute(f'SELECT COUNT(*) AS n FROM "{safe_table}"')
        count_row = await count_cur.fetchone()
        return {
            "entity": entity,
            "table": table,
            "reachable": True,
            "columns": columns,
            "row_count": count_row["n"] if count_row else None,
            "sample_rows": [{k: _truncate(r[k]) for k in r.keys()} for r in rows],
            "error": None,
        }
    except Exception as exc:
        return _empty_table_result(entity, table, str(exc))


# --- SQL Server ------------------------------------------------------------
# No lightweight async driver is a safe default here, so this one runs the
# (blocking) pymssql client in a worker thread rather than pulling in ODBC.

async def _test_sqlserver(connection: dict, tables: list[dict]) -> dict:
    try:
        import pymssql
    except ImportError:
        return {
            "connected": False,
            "error": (
                "No SQL Server driver is installed on this Kernel yet (pip install pymssql). "
                "Your connection details weren't rejected - install the driver to run a live preview."
            ),
            "tables": [],
        }

    def _run() -> list[dict]:
        conn = pymssql.connect(
            server=connection.get("host"),
            port=str(connection.get("port") or 1433),
            database=connection.get("database"),
            user=connection.get("username"),
            password=connection.get("password"),
            login_timeout=_CONNECT_TIMEOUT,
            timeout=_CONNECT_TIMEOUT,
        )
        table_results = []
        try:
            cur = conn.cursor(as_dict=True)
            for entry in tables:
                entity, table = entry["entity"], entry["table"]
                safe_table = _safe_identifier(table)
                if not safe_table:
                    table_results.append(_empty_table_result(entity, table, "Not a valid table name"))
                    continue
                try:
                    cur.execute(f"SELECT TOP {_SAMPLE_ROWS} * FROM [{safe_table}]")
                    rows = cur.fetchall()
                    cur.execute(f"SELECT COUNT(*) AS n FROM [{safe_table}]")
                    count_row = cur.fetchone()
                    columns = list(rows[0].keys()) if rows else []
                    table_results.append({
                        "entity": entity,
                        "table": table,
                        "reachable": True,
                        "columns": columns,
                        "row_count": count_row["n"] if count_row else None,
                        "sample_rows": [{k: _truncate(v) for k, v in r.items()} for r in rows],
                        "error": None,
                    })
                except Exception as exc:
                    table_results.append(_empty_table_result(entity, table, str(exc)))
        finally:
            conn.close()
        return table_results

    loop = asyncio.get_running_loop()
    try:
        table_results = await loop.run_in_executor(None, _run)
    except Exception as exc:
        return {"connected": False, "error": str(exc), "tables": []}
    return {"connected": True, "error": None, "tables": table_results}


_HANDLERS = {
    "postgresql": _test_postgresql,
    "mysql": _test_mysql,
    "mongodb": _test_mongodb,
    "sqlserver": _test_sqlserver,
    "sqlite": _test_sqlite,
}
