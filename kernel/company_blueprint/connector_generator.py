"""
Connector Generator

The SDK Generator (sdk_generator.py) hands a company starter code for
talking OUT to Orbit's webhook endpoint. This module is the other
direction: starter code that runs on the COMPANY's own side and reads
FROM their database (employees, invoices, inventory, payments, or
whatever else their Blueprint needs) so it can be forwarded to Orbit.

Same non-negotiable as the SDK Generator: never embed a live secret in
generated source. The connection block below always reads host/port/
database/username from environment variables at runtime; only the
values that are safe to see in a copy-pasted sample (host, port,
database name, username, the table map) are pre-filled as defaults -
the password is NEVER interpolated into the file, even though the user
typed it into the wizard to run the live Test Connection.

Every generated file also ships an HTTP entrypoint, because the whole
point of this file is to run on the COMPANY's own hosting (a shared
PHP host, a small VPS, etc.) where Orbit's Kernel can't reach the
database directly but can reach a URL. Once the company uploads/runs
the file, they paste that file's live URL into the Connector URL field
in the wizard so the Kernel knows where to call for `?entity=...`
reads - see connector_tester.py's `_test_via_url`.

The entrypoint is open (unauthenticated) by default - Design choice:
the company owns this file after generation, so the ORBIT_CONNECTOR_TOKEN
block is left in plainly, commented, and editable rather than hidden or
enforced, so they can switch it on themselves if they want to lock the
URL down (e.g. once it's public on a real domain instead of a private
network).
"""

from __future__ import annotations

import re

CONNECTOR_LANGUAGES = ["javascript", "php", "python", "java"]
CONNECTOR_DATABASES = ["postgresql", "mysql", "mongodb", "sqlserver", "sqlite"]

_EXTENSIONS = {"javascript": "js", "php": "php", "python": "py", "java": "java"}

_DEFAULT_PORTS = {"postgresql": 5432, "mysql": 3306, "mongodb": 27017, "sqlserver": 1433, "sqlite": None}

_DEFAULT_TABLES = [
    {"entity": "employees", "table": "employees", "id_column": "id"},
    {"entity": "invoices", "table": "invoices", "id_column": "id"},
    {"entity": "inventory", "table": "inventory", "id_column": "id"},
    {"entity": "payments", "table": "payments", "id_column": "id"},
]

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConnectorValidationError(ValueError):
    pass


def _clean_entity(raw: str, fallback: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return fallback
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_").lower()
    return slug or fallback


def _clean_tables(tables: list[dict] | None) -> list[dict]:
    if not tables:
        return list(_DEFAULT_TABLES)
    cleaned = []
    for i, t in enumerate(tables):
        if not isinstance(t, dict):
            continue
        entity = _clean_entity(t.get("entity"), f"table_{i + 1}")
        table = str(t.get("table") or "").strip()
        id_column = str(t.get("id_column") or "id").strip() or "id"
        if table:
            cleaned.append({"entity": entity, "table": table, "id_column": id_column})
    return cleaned or list(_DEFAULT_TABLES)


def _clean_connection(database: str, connection: dict | None) -> dict:
    connection = connection or {}
    return {
        "host": str(connection.get("host") or ("./orbit.sqlite" if database == "sqlite" else "localhost")),
        "port": connection.get("port") or _DEFAULT_PORTS.get(database),
        "database": str(connection.get("database") or "your_database"),
        "username": str(connection.get("username") or "your_username"),
        "ssl": bool(connection.get("ssl")),
    }


def resolve_filename(language: str, filename: str | None) -> str:
    ext = _EXTENSIONS[language]
    filename = (filename or "").strip()
    filename = re.sub(r"[\\/]+", "", filename)  # no path traversal in a download name
    if not filename:
        return f"orbit-connector.{ext}"
    if not filename.endswith(f".{ext}"):
        filename = f"{filename.rsplit('.', 1)[0] if '.' in filename else filename}.{ext}"
    return filename


# --- JavaScript --------------------------------------------------------

_JS_DB = {
    "postgresql": {
        "install": "npm install pg",
        "require": 'const { Client } = require("pg");',
        "connect": """  const client = new Client({
    host: ORBIT_DB_CONFIG.host,
    port: ORBIT_DB_CONFIG.port,
    database: ORBIT_DB_CONFIG.database,
    user: ORBIT_DB_CONFIG.user,
    password: ORBIT_DB_CONFIG.password,
    ssl: ORBIT_DB_CONFIG.ssl ? { rejectUnauthorized: false } : false,
  });
  await client.connect();""",
        "read": """  const { rows } = await client.query(`SELECT * FROM "${table}" LIMIT ${limit}`);
  return rows;""",
        "close": "  await client.end();",
    },
    "mysql": {
        "install": "npm install mysql2",
        "require": 'const mysql = require("mysql2/promise");',
        "connect": """  const client = await mysql.createConnection({
    host: ORBIT_DB_CONFIG.host,
    port: ORBIT_DB_CONFIG.port,
    database: ORBIT_DB_CONFIG.database,
    user: ORBIT_DB_CONFIG.user,
    password: ORBIT_DB_CONFIG.password,
    ssl: ORBIT_DB_CONFIG.ssl ? {} : undefined,
  });""",
        "read": """  const [rows] = await client.query(`SELECT * FROM \\`${table}\\` LIMIT ${limit}`);
  return rows;""",
        "close": "  await client.end();",
    },
    "sqlserver": {
        "install": "npm install mssql",
        "require": 'const sql = require("mssql");',
        "connect": """  const client = await sql.connect({
    server: ORBIT_DB_CONFIG.host,
    port: Number(ORBIT_DB_CONFIG.port),
    database: ORBIT_DB_CONFIG.database,
    user: ORBIT_DB_CONFIG.user,
    password: ORBIT_DB_CONFIG.password,
    options: { encrypt: ORBIT_DB_CONFIG.ssl },
  });""",
        "read": """  const result = await client.request().query(`SELECT TOP ${limit} * FROM [${table}]`);
  return result.recordset;""",
        "close": "  await client.close();",
    },
    "sqlite": {
        "install": "npm install sqlite3 sqlite",
        "require": 'const sqlite3 = require("sqlite3");\nconst { open } = require("sqlite");',
        "connect": """  const client = await open({ filename: ORBIT_DB_CONFIG.host, driver: sqlite3.Database });""",
        "read": """  const rows = await client.all(`SELECT * FROM "${table}" LIMIT ${limit}`);
  return rows;""",
        "close": "  await client.close();",
    },
}


def _javascript(database: str, connection: dict, tables: list[dict]) -> str:
    table_map = ",\n".join(
        f'  {t["entity"]}: {{ table: "{t["table"]}", idColumn: "{t["id_column"]}" }}' for t in tables
    )

    if database == "mongodb":
        return f"""/**
 * Orbit Connector - MongoDB
 * {_install_note("javascript", database)}
 *
 * Edit ORBIT_TABLE_MAP below to point each Orbit entity at your real
 * collection name. ORBIT_DB_CONFIG reads host/port/db/user from the
 * environment - only the password is ever read from an env var, never
 * hardcoded here.
 */
const {{ MongoClient }} = require("mongodb");

const ORBIT_DB_CONFIG = {{
  host: process.env.ORBIT_DB_HOST || "{connection['host']}",
  port: process.env.ORBIT_DB_PORT || {connection['port']},
  database: process.env.ORBIT_DB_NAME || "{connection['database']}",
  user: process.env.ORBIT_DB_USER || "{connection['username']}",
  password: process.env.ORBIT_DB_PASSWORD, // never hardcoded
  ssl: {str(connection['ssl']).lower()},
}};

// Map each Orbit entity Orbit needs -> your collection name.
// Leave a value out if you don't have that collection.
const ORBIT_TABLE_MAP = {{
{table_map}
}};

async function readCollection(entityKey, limit = 5) {{
  const entry = ORBIT_TABLE_MAP[entityKey];
  if (!entry) throw new Error(`No collection mapped for "${{entityKey}}"`);

  const auth = ORBIT_DB_CONFIG.user ? `${{ORBIT_DB_CONFIG.user}}:${{ORBIT_DB_CONFIG.password}}@` : "";
  const uri = `mongodb://${{auth}}${{ORBIT_DB_CONFIG.host}}:${{ORBIT_DB_CONFIG.port}}/${{ORBIT_DB_CONFIG.database}}`;
  const client = new MongoClient(uri, {{ tls: ORBIT_DB_CONFIG.ssl }});
  await client.connect();
  try {{
    const docs = await client
      .db(ORBIT_DB_CONFIG.database)
      .collection(entry.table)
      .find({{}})
      .limit(limit)
      .toArray();
    return docs;
  }} finally {{
    await client.close();
  }}
}}

module.exports = {{ ORBIT_DB_CONFIG, ORBIT_TABLE_MAP, readCollection }};

{_js_http_entrypoint("readCollection(entity, limit)")}
"""

    spec = _JS_DB[database]
    return f"""/**
 * Orbit Connector - {database}
 * {_install_note("javascript", database)}
 *
 * Edit ORBIT_TABLE_MAP below to point each Orbit entity at your real
 * table name. ORBIT_DB_CONFIG reads host/port/db/user from the
 * environment - only the password is ever read from an env var, never
 * hardcoded here.
 */
{spec['require']}

const ORBIT_DB_CONFIG = {{
  host: process.env.ORBIT_DB_HOST || "{connection['host']}",
  port: process.env.ORBIT_DB_PORT || {connection['port']},
  database: process.env.ORBIT_DB_NAME || "{connection['database']}",
  user: process.env.ORBIT_DB_USER || "{connection['username']}",
  password: process.env.ORBIT_DB_PASSWORD, // never hardcoded
  ssl: {str(connection['ssl']).lower()},
}};

// Map each Orbit entity -> your real table name (and id column, if
// you want Orbit to track it). Leave an entry out if you don't have
// that table.
const ORBIT_TABLE_MAP = {{
{table_map}
}};

async function readTable(entityKey, limit = 5) {{
  const entry = ORBIT_TABLE_MAP[entityKey];
  if (!entry) throw new Error(`No table mapped for "${{entityKey}}"`);
  const table = entry.table;

{spec['connect']}
  try {{
{spec['read']}
  }} finally {{
{spec['close']}
  }}
}}

module.exports = {{ ORBIT_DB_CONFIG, ORBIT_TABLE_MAP, readTable }};

{_js_http_entrypoint("readTable(entity, limit)")}
"""


# --- PHP -----------------------------------------------------------------

_PHP_DSN = {
    "postgresql": '"pgsql:host=" . $ORBIT_DB_CONFIG[\'host\'] . ";port=" . $ORBIT_DB_CONFIG[\'port\'] . ";dbname=" . $ORBIT_DB_CONFIG[\'database\']',
    "mysql": '"mysql:host=" . $ORBIT_DB_CONFIG[\'host\'] . ";port=" . $ORBIT_DB_CONFIG[\'port\'] . ";dbname=" . $ORBIT_DB_CONFIG[\'database\'] . ";charset=utf8mb4"',
    "sqlserver": '"sqlsrv:Server=" . $ORBIT_DB_CONFIG[\'host\'] . "," . $ORBIT_DB_CONFIG[\'port\'] . ";Database=" . $ORBIT_DB_CONFIG[\'database\']',
    "sqlite": '"sqlite:" . $ORBIT_DB_CONFIG[\'host\']',
}

_PHP_QUOTE = {"postgresql": '"', "mysql": "`", "sqlserver": "[", "sqlite": '"'}
_PHP_QUOTE_CLOSE = {"postgresql": '"', "mysql": "`", "sqlserver": "]", "sqlite": '"'}


def _js_http_entrypoint(read_call: str) -> str:
    """
    Shared HTTP entrypoint for the JS connector - a plain Node `http`
    server (no framework needed) so `node orbit-connector.js` gives
    you a URL to paste into the wizard's Connector URL field. Same
    open-by-default ORBIT_CONNECTOR_TOKEN as the PHP version - unset
    means open, set it (and send it back as X-Orbit-Token) to lock it
    down yourself once this is live somewhere.
    """
    return f"""// --- HTTP entrypoint -----------------------------------------------
// Run this file directly (`node {{this file}}`) to serve it over HTTP -
// that gives you the URL to paste into the Orbit wizard's Connector URL
// field, e.g. http://your-host:3000/?entity=employees&limit=5
//
// Open by default - edit/remove this block, or set ORBIT_CONNECTOR_TOKEN,
// however you want to trust or lock this down. It's your file.
if (require.main === module) {{
  const http = require("http");
  const {{ URL }} = require("url");

  // Optional shared secret - unset (the default) means open access.
  const ORBIT_CONNECTOR_TOKEN = process.env.ORBIT_CONNECTOR_TOKEN || null;
  const PORT = process.env.PORT || 3000;

  const server = http.createServer(async (req, res) => {{
    const url = new URL(req.url, `http://${{req.headers.host}}`);
    res.setHeader("Content-Type", "application/json");

    if (ORBIT_CONNECTOR_TOKEN && req.headers["x-orbit-token"] !== ORBIT_CONNECTOR_TOKEN) {{
      res.statusCode = 401;
      res.end(JSON.stringify({{ ok: false, error: "invalid or missing X-Orbit-Token" }}));
      return;
    }}

    const entity = url.searchParams.get("entity");
    const limit = Number(url.searchParams.get("limit") || 5);

    if (entity === "_health") {{
      res.end(JSON.stringify({{ ok: true, entities: Object.keys(ORBIT_TABLE_MAP) }}));
      return;
    }}
    if (!entity) {{
      res.statusCode = 400;
      res.end(JSON.stringify({{ ok: false, error: "pass ?entity=<name>, e.g. ?entity=employees" }}));
      return;
    }}

    try {{
      const rows = await {read_call};
      res.end(JSON.stringify({{ ok: true, entity, rows }}));
    }} catch (err) {{
      res.statusCode = 500;
      res.end(JSON.stringify({{ ok: false, entity, error: err.message }}));
    }}
  }});

  server.listen(PORT, () => console.log(`Orbit connector listening on :${{PORT}}`));
}}"""


def _py_http_entrypoint(read_call: str) -> str:
    """
    Shared HTTP entrypoint for the Python connector - built on the
    standard library's http.server, so `python orbit-connector.py`
    alone gives you the URL to paste into the wizard's Connector URL
    field. Same open-by-default ORBIT_CONNECTOR_TOKEN as the other
    languages - unset means open.
    """
    return f'''# --- HTTP entrypoint -----------------------------------------------
# Run this file directly (`python {{this file}}`) to serve it over HTTP -
# that gives you the URL to paste into the Orbit wizard's Connector URL
# field, e.g. http://your-host:8000/?entity=employees&limit=5
#
# Open by default - edit/remove this block, or set ORBIT_CONNECTOR_TOKEN,
# however you want to trust or lock this down. It's your file.
if __name__ == "__main__":
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import urlparse, parse_qs

    ORBIT_CONNECTOR_TOKEN = os.environ.get("ORBIT_CONNECTOR_TOKEN")  # unset = open access
    PORT = int(os.environ.get("PORT", 8000))

    class OrbitConnectorHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if ORBIT_CONNECTOR_TOKEN and self.headers.get("X-Orbit-Token") != ORBIT_CONNECTOR_TOKEN:
                self._respond(401, {{"ok": False, "error": "invalid or missing X-Orbit-Token"}})
                return

            query = parse_qs(urlparse(self.path).query)
            entity = (query.get("entity") or [None])[0]
            limit = int((query.get("limit") or [5])[0])

            if entity == "_health":
                self._respond(200, {{"ok": True, "entities": list(ORBIT_TABLE_MAP.keys())}})
                return
            if not entity:
                self._respond(400, {{"ok": False, "error": "pass ?entity=<name>, e.g. ?entity=employees"}})
                return

            try:
                rows = {read_call}
                self._respond(200, {{"ok": True, "entity": entity, "rows": rows}})
            except Exception as exc:
                self._respond(500, {{"ok": False, "entity": entity, "error": str(exc)}})

        def _respond(self, status: int, payload: dict):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, default=str).encode())

        def log_message(self, format, *args):
            pass  # keep stdout clean; remove this to see request logs

    HTTPServer(("0.0.0.0", PORT), OrbitConnectorHandler).serve_forever()'''


def _php_http_entrypoint(read_call: str) -> str:
    """
    Shared HTTP entrypoint appended to every PHP connector. This is
    the part that makes "paste this file's URL into the wizard" work:
    once uploaded to a web host, hitting the URL with ?entity=... runs
    the read function above and returns JSON, so the Kernel can pull
    from a database it could never reach directly.

    ORBIT_CONNECTOR_TOKEN is intentionally OPEN by default (no token
    set = no check). It's a plain, editable line, not a hidden setting
    - turn it on yourself by setting the env var (or hardcoding a
    value here) once this file is live on a real URL, and send the
    same value back as the X-Orbit-Token header from the wizard.
    """
    return f"""// --- HTTP entrypoint -----------------------------------------------
// This is what turns this file into the URL you paste into the Orbit
// wizard's "Connector URL" field. Deploy this file anywhere PHP runs
// (shared hosting is fine) and call it like:
//   https://your-host.example.com/orbit-connector.php?entity=employees&limit=5
//
// Open by default - edit/remove this block, or set ORBIT_CONNECTOR_TOKEN,
// however you want to trust or lock this down. It's your file.
if (php_sapi_name() !== "cli" && basename($_SERVER["SCRIPT_FILENAME"] ?? "") === basename(__FILE__)) {{
    header("Content-Type: application/json");

    // Optional shared secret - unset (the default) means open access.
    // Set ORBIT_CONNECTOR_TOKEN in your hosting env to require callers
    // to send a matching X-Orbit-Token header.
    $ORBIT_CONNECTOR_TOKEN = getenv("ORBIT_CONNECTOR_TOKEN") ?: null;
    if ($ORBIT_CONNECTOR_TOKEN) {{
        $sent = $_SERVER["HTTP_X_ORBIT_TOKEN"] ?? "";
        if (!hash_equals($ORBIT_CONNECTOR_TOKEN, $sent)) {{
            http_response_code(401);
            echo json_encode(["ok" => false, "error" => "invalid or missing X-Orbit-Token"]);
            exit;
        }}
    }}

    $entity = $_GET["entity"] ?? null;
    $limit = isset($_GET["limit"]) ? (int) $_GET["limit"] : 5;

    if ($entity === "_health") {{
        echo json_encode(["ok" => true, "entities" => array_keys($ORBIT_TABLE_MAP)]);
        exit;
    }}
    if (!$entity) {{
        http_response_code(400);
        echo json_encode(["ok" => false, "error" => "pass ?entity=<name>, e.g. ?entity=employees"]);
        exit;
    }}

    try {{
        $rows = {read_call};
        echo json_encode(["ok" => true, "entity" => $entity, "rows" => $rows]);
    }} catch (Throwable $e) {{
        http_response_code(500);
        echo json_encode(["ok" => false, "entity" => $entity, "error" => $e->getMessage()]);
    }}
}}"""


def _php(database: str, connection: dict, tables: list[dict]) -> str:
    table_map = ",\n".join(
        f'    "{t["entity"]}" => ["table" => "{t["table"]}", "id_column" => "{t["id_column"]}"]' for t in tables
    )

    if database == "mongodb":
        return f"""<?php
/**
 * Orbit Connector - MongoDB
 * {_install_note("php", database)}
 *
 * Edit ORBIT_TABLE_MAP to point each Orbit entity at your real
 * collection name. The password is read only from the environment -
 * it is never written into this file.
 */

$ORBIT_DB_CONFIG = [
    "host" => getenv("ORBIT_DB_HOST") ?: "{connection['host']}",
    "port" => getenv("ORBIT_DB_PORT") ?: {connection['port']},
    "database" => getenv("ORBIT_DB_NAME") ?: "{connection['database']}",
    "user" => getenv("ORBIT_DB_USER") ?: "{connection['username']}",
    "password" => getenv("ORBIT_DB_PASSWORD"), // never hardcoded
    "ssl" => {str(connection['ssl']).lower()},
];

$ORBIT_TABLE_MAP = [
{table_map}
];

function orbit_read_collection(string $entityKey, int $limit = 5): array {{
    global $ORBIT_DB_CONFIG, $ORBIT_TABLE_MAP;
    if (!isset($ORBIT_TABLE_MAP[$entityKey])) {{
        throw new Exception("No collection mapped for \\"$entityKey\\"");
    }}
    $collectionName = $ORBIT_TABLE_MAP[$entityKey]["table"];

    $auth = $ORBIT_DB_CONFIG["user"]
        ? "{{$ORBIT_DB_CONFIG['user']}}:{{$ORBIT_DB_CONFIG['password']}}@"
        : "";
    $uri = "mongodb://{{$auth}}{{$ORBIT_DB_CONFIG['host']}}:{{$ORBIT_DB_CONFIG['port']}}";

    $client = new MongoDB\\Client($uri);
    $collection = $client->{{$ORBIT_DB_CONFIG['database']}}->$collectionName;
    $cursor = $collection->find([], ["limit" => $limit]);
    return iterator_to_array($cursor, false);
}}

{_php_http_entrypoint("orbit_read_collection($entity, $limit)")}
"""

    dsn_expr = _PHP_DSN[database]
    q, qc = _PHP_QUOTE[database], _PHP_QUOTE_CLOSE[database]

    if database == "sqlserver":
        query_line = f'$sql = "SELECT TOP " . (int) $limit . " * FROM {q}" . $table . "{qc}";'
    else:
        query_line = f'$sql = "SELECT * FROM {q}" . $table . "{qc} LIMIT " . (int) $limit;'

    return f"""<?php
/**
 * Orbit Connector - {database}
 * {_install_note("php", database)}
 *
 * Edit ORBIT_TABLE_MAP to point each Orbit entity at your real table
 * name and id column. The password is read only from the environment -
 * it is never written into this file.
 */

$ORBIT_DB_CONFIG = [
    "host" => getenv("ORBIT_DB_HOST") ?: "{connection['host']}",
    "port" => getenv("ORBIT_DB_PORT") ?: {connection['port']},
    "database" => getenv("ORBIT_DB_NAME") ?: "{connection['database']}",
    "user" => getenv("ORBIT_DB_USER") ?: "{connection['username']}",
    "password" => getenv("ORBIT_DB_PASSWORD"), // never hardcoded
    "ssl" => {str(connection['ssl']).lower()},
];

// Map each Orbit entity -> your real table name (and id column).
// Leave an entry out if you don't have that table.
$ORBIT_TABLE_MAP = [
{table_map}
];

function orbit_connect(): PDO {{
    global $ORBIT_DB_CONFIG;
    // Built from $ORBIT_DB_CONFIG every time this runs - edit the config
    // array above, not this line, if your host/port/database changes.
    $dsn = {dsn_expr};
    return new PDO($dsn, $ORBIT_DB_CONFIG["user"], $ORBIT_DB_CONFIG["password"], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
}}

function orbit_read_table(string $entityKey, int $limit = 5): array {{
    global $ORBIT_TABLE_MAP;
    if (!isset($ORBIT_TABLE_MAP[$entityKey])) {{
        throw new Exception("No table mapped for \\"$entityKey\\"");
    }}
    $table = $ORBIT_TABLE_MAP[$entityKey]["table"];
    $pdo = orbit_connect();
    {query_line}
    $stmt = $pdo->query($sql);
    return $stmt->fetchAll();
}}

{_php_http_entrypoint("orbit_read_table($entity, $limit)")}
"""


# --- Python ----------------------------------------------------------------

_PY_DB = {
    "postgresql": {
        "install": "pip install psycopg2-binary",
        "import": "import psycopg2\nimport psycopg2.extras",
        "connect": """    return psycopg2.connect(
        host=ORBIT_DB_CONFIG["host"],
        port=ORBIT_DB_CONFIG["port"],
        dbname=ORBIT_DB_CONFIG["database"],
        user=ORBIT_DB_CONFIG["user"],
        password=ORBIT_DB_CONFIG["password"],
        sslmode="require" if ORBIT_DB_CONFIG["ssl"] else "prefer",
    )""",
        "read": """    conn = orbit_connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f'SELECT * FROM "{table}" LIMIT %s', (limit,))
            return cur.fetchall()
    finally:
        conn.close()""",
    },
    "mysql": {
        "install": "pip install pymysql",
        "import": "import pymysql\nimport pymysql.cursors",
        "connect": """    return pymysql.connect(
        host=ORBIT_DB_CONFIG["host"],
        port=ORBIT_DB_CONFIG["port"],
        db=ORBIT_DB_CONFIG["database"],
        user=ORBIT_DB_CONFIG["user"],
        password=ORBIT_DB_CONFIG["password"],
        ssl={"ssl": {}} if ORBIT_DB_CONFIG["ssl"] else None,
        cursorclass=pymysql.cursors.DictCursor,
    )""",
        "read": """    conn = orbit_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{table}` LIMIT %s", (limit,))
            return cur.fetchall()
    finally:
        conn.close()""",
    },
    "sqlserver": {
        "install": "pip install pymssql",
        "import": "import pymssql",
        "connect": """    return pymssql.connect(
        server=ORBIT_DB_CONFIG["host"],
        port=str(ORBIT_DB_CONFIG["port"]),
        database=ORBIT_DB_CONFIG["database"],
        user=ORBIT_DB_CONFIG["user"],
        password=ORBIT_DB_CONFIG["password"],
    )""",
        "read": """    conn = orbit_connect()
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute(f"SELECT TOP {limit} * FROM [{table}]")
            return cur.fetchall()
    finally:
        conn.close()""",
    },
    "sqlite": {
        "install": "# sqlite3 is in the Python standard library",
        "import": "import sqlite3",
        "connect": """    conn = sqlite3.connect(ORBIT_DB_CONFIG["host"])
    conn.row_factory = sqlite3.Row
    return conn""",
        "read": """    conn = orbit_connect()
    try:
        cur = conn.execute(f'SELECT * FROM "{table}" LIMIT ?', (limit,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()""",
    },
}


def _python(database: str, connection: dict, tables: list[dict]) -> str:
    table_map = ",\n".join(
        f'    "{t["entity"]}": {{"table": "{t["table"]}", "id_column": "{t["id_column"]}"}}' for t in tables
    )

    if database == "mongodb":
        return f'''"""
Orbit Connector - MongoDB
{_install_note("python", database)}

Edit ORBIT_TABLE_MAP to point each Orbit entity at your real collection
name. The password is read only from the environment - it is never
written into this file.
"""

import os

from pymongo import MongoClient

ORBIT_DB_CONFIG = {{
    "host": os.environ.get("ORBIT_DB_HOST", "{connection['host']}"),
    "port": int(os.environ.get("ORBIT_DB_PORT", {connection['port']})),
    "database": os.environ.get("ORBIT_DB_NAME", "{connection['database']}"),
    "user": os.environ.get("ORBIT_DB_USER", "{connection['username']}"),
    "password": os.environ.get("ORBIT_DB_PASSWORD"),  # never hardcoded
    "ssl": {connection['ssl']},
}}

ORBIT_TABLE_MAP = {{
{table_map}
}}


def orbit_read_collection(entity_key: str, limit: int = 5) -> list[dict]:
    if entity_key not in ORBIT_TABLE_MAP:
        raise ValueError(f"No collection mapped for '{{entity_key}}'")
    collection_name = ORBIT_TABLE_MAP[entity_key]["table"]

    auth = f"{{ORBIT_DB_CONFIG['user']}}:{{ORBIT_DB_CONFIG['password']}}@" if ORBIT_DB_CONFIG["user"] else ""
    uri = f"mongodb://{{auth}}{{ORBIT_DB_CONFIG['host']}}:{{ORBIT_DB_CONFIG['port']}}"
    client = MongoClient(uri, tls=ORBIT_DB_CONFIG["ssl"])
    try:
        db = client[ORBIT_DB_CONFIG["database"]]
        return list(db[collection_name].find().limit(limit))
    finally:
        client.close()


{_py_http_entrypoint("orbit_read_collection(entity, limit)")}
'''

    spec = _PY_DB[database]
    return f'''"""
Orbit Connector - {database}
{_install_note("python", database)}

Edit ORBIT_TABLE_MAP to point each Orbit entity at your real table
name and id column. The password is read only from the environment -
it is never written into this file.
"""

import os

{spec['import']}

ORBIT_DB_CONFIG = {{
    "host": os.environ.get("ORBIT_DB_HOST", "{connection['host']}"),
    "port": int(os.environ.get("ORBIT_DB_PORT", {connection['port']})),
    "database": os.environ.get("ORBIT_DB_NAME", "{connection['database']}"),
    "user": os.environ.get("ORBIT_DB_USER", "{connection['username']}"),
    "password": os.environ.get("ORBIT_DB_PASSWORD"),  # never hardcoded
    "ssl": {connection['ssl']},
}}

# Map each Orbit entity -> your real table name (and id column).
# Leave an entry out if you don't have that table.
ORBIT_TABLE_MAP = {{
{table_map}
}}


def orbit_connect():
{spec['connect']}


def orbit_read_table(entity_key: str, limit: int = 5) -> list[dict]:
    if entity_key not in ORBIT_TABLE_MAP:
        raise ValueError(f"No table mapped for '{{entity_key}}'")
    table = ORBIT_TABLE_MAP[entity_key]["table"]
{spec['read']}


{_py_http_entrypoint("orbit_read_table(entity, limit)")}
'''


# --- Java --------------------------------------------------------------

_JAVA_JDBC = {
    "postgresql": 'jdbc:postgresql://{host}:{port}/{database}{ssl}',
    "mysql": 'jdbc:mysql://{host}:{port}/{database}{ssl}',
    "sqlserver": 'jdbc:sqlserver://{host}:{port};databaseName={database}{ssl}',
    "sqlite": 'jdbc:sqlite:{host}',
}

# Same URLs as _JAVA_JDBC above, but as Java string-concatenation
# expressions built from HOST/PORT/DATABASE at runtime instead of
# baked-in literals - {ssl} is still filled in at generation time
# since it only reflects the wizard's SSL checkbox, not something
# meant to be edited per-deploy the way host/port/database are.
_JAVA_JDBC_EXPR = {
    "postgresql": '"jdbc:postgresql://" + HOST + ":" + PORT + "/" + DATABASE + "{ssl}"',
    "mysql": '"jdbc:mysql://" + HOST + ":" + PORT + "/" + DATABASE + "{ssl}"',
    "sqlserver": '"jdbc:sqlserver://" + HOST + ":" + PORT + ";databaseName=" + DATABASE + "{ssl}"',
    "sqlite": '"jdbc:sqlite:" + HOST',
}
_JAVA_DRIVER_CLASS = {
    "postgresql": "org.postgresql.Driver",
    "mysql": "com.mysql.cj.jdbc.Driver",
    "sqlserver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
    "sqlite": "org.sqlite.JDBC",
}
_JAVA_QUOTE = {"postgresql": '"', "mysql": "`", "sqlserver": "[", "sqlite": '"'}
_JAVA_QUOTE_CLOSE = {"postgresql": '"', "mysql": "`", "sqlserver": "]", "sqlite": '"'}


def _java_http_entrypoint(read_call: str) -> str:
    """
    Shared HTTP entrypoint for the Java connector, using the JDK's
    built-in com.sun.net.httpserver (no extra dependency needed) so
    `java OrbitConnector` alone gives you a URL to paste into the
    wizard's Connector URL field. Same open-by-default
    ORBIT_CONNECTOR_TOKEN as the other languages, and a tiny hand-rolled
    JSON writer since we don't want to force a JSON library dependency
    on every reader of this file.
    """
    return f"""
    // --- HTTP entrypoint -------------------------------------------
    // Run this directly (`java OrbitConnector`, after compiling) to serve
    // it over HTTP - that gives you the URL to paste into the Orbit
    // wizard's Connector URL field, e.g. http://your-host:8080/?entity=employees&limit=5
    //
    // Open by default - edit/remove this block, or set ORBIT_CONNECTOR_TOKEN,
    // however you want to trust or lock this down. It's your file.
    public static void main(String[] args) throws Exception {{
        String token = System.getenv("ORBIT_CONNECTOR_TOKEN"); // unset = open access
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));

        com.sun.net.httpserver.HttpServer server =
            com.sun.net.httpserver.HttpServer.create(new java.net.InetSocketAddress(port), 0);
        server.createContext("/", exchange -> {{
            java.util.Map<String, String> query = parseQuery(exchange.getRequestURI().getRawQuery());
            String sent = exchange.getRequestHeaders().getFirst("X-Orbit-Token");
            try {{
                if (token != null && !token.isEmpty() && !token.equals(sent)) {{
                    respond(exchange, 401, "{{\\"ok\\":false,\\"error\\":\\"invalid or missing X-Orbit-Token\\"}}");
                    return;
                }}
                String entity = query.get("entity");
                int limit = query.containsKey("limit") ? Integer.parseInt(query.get("limit")) : 5;

                if ("_health".equals(entity)) {{
                    respond(exchange, 200, "{{\\"ok\\":true,\\"entities\\":" + jsonArray(ORBIT_TABLE_MAP.keySet()) + "}}");
                    return;
                }}
                if (entity == null) {{
                    respond(exchange, 400, "{{\\"ok\\":false,\\"error\\":\\"pass ?entity=<name>, e.g. ?entity=employees\\"}}");
                    return;
                }}
                Object rows = {read_call};
                respond(exchange, 200, "{{\\"ok\\":true,\\"entity\\":\\"" + entity + "\\",\\"rows\\":" + toJson(rows) + "}}");
            }} catch (Exception e) {{
                respond(exchange, 500, "{{\\"ok\\":false,\\"error\\":\\"" + jsonEscape(e.getMessage()) + "\\"}}");
            }}
        }});
        server.start();
        System.out.println("Orbit connector listening on :" + port);
    }}

    private static java.util.Map<String, String> parseQuery(String raw) {{
        java.util.Map<String, String> out = new java.util.HashMap<>();
        if (raw == null) return out;
        for (String pair : raw.split("&")) {{
            String[] kv = pair.split("=", 2);
            if (kv.length == 2) out.put(java.net.URLDecoder.decode(kv[0], java.nio.charset.StandardCharsets.UTF_8),
                                         java.net.URLDecoder.decode(kv[1], java.nio.charset.StandardCharsets.UTF_8));
        }}
        return out;
    }}

    private static void respond(com.sun.net.httpserver.HttpExchange exchange, int status, String body) throws java.io.IOException {{
        byte[] bytes = body.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        try (java.io.OutputStream os = exchange.getResponseBody()) {{
            os.write(bytes);
        }}
    }}

    private static String jsonEscape(Object value) {{
        return String.valueOf(value).replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"");
    }}

    private static String jsonArray(java.util.Collection<?> values) {{
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (Object v : values) {{
            if (!first) sb.append(",");
            sb.append("\\"").append(jsonEscape(v)).append("\\"");
            first = false;
        }}
        return sb.append("]").toString();
    }}

    // Minimal, dependency-free serializer - good enough for the flat
    // rows this connector returns. Swap in a real JSON library
    // (Jackson/Gson) if your rows get more complex than that.
    @SuppressWarnings("unchecked")
    private static String toJson(Object value) {{
        if (value == null) return "null";
        if (value instanceof java.util.List) {{
            StringBuilder sb = new StringBuilder("[");
            boolean first = true;
            for (Object item : (java.util.List<Object>) value) {{
                if (!first) sb.append(",");
                sb.append(toJson(item));
                first = false;
            }}
            return sb.append("]").toString();
        }}
        if (value instanceof java.util.Map) {{
            StringBuilder sb = new StringBuilder("{{");
            boolean first = true;
            for (java.util.Map.Entry<?, ?> entry : ((java.util.Map<?, ?>) value).entrySet()) {{
                if (!first) sb.append(",");
                sb.append("\\"").append(jsonEscape(entry.getKey())).append("\\":").append(toJson(entry.getValue()));
                first = false;
            }}
            return sb.append("}}").toString();
        }}
        if (value instanceof Number || value instanceof Boolean) return String.valueOf(value);
        return "\\"" + jsonEscape(value) + "\\"";
    }}"""


def _java(database: str, connection: dict, tables: list[dict]) -> str:
    table_map = "\n".join(
        f'        put("{t["entity"]}", "{t["table"]}");' for t in tables
    )

    if database == "mongodb":
        return f"""/**
 * Orbit Connector - MongoDB
 * {_install_note("java", database)}
 *
 * Edit ORBIT_TABLE_MAP to point each Orbit entity at your real
 * collection name. The password is read only from the environment -
 * it is never written into this file.
 */
import com.mongodb.client.*;
import org.bson.Document;

import java.util.*;

public class OrbitConnector {{
    static final String HOST = System.getenv().getOrDefault("ORBIT_DB_HOST", "{connection['host']}");
    static final int PORT = Integer.parseInt(System.getenv().getOrDefault("ORBIT_DB_PORT", "{connection['port']}"));
    static final String DATABASE = System.getenv().getOrDefault("ORBIT_DB_NAME", "{connection['database']}");
    static final String USER = System.getenv().getOrDefault("ORBIT_DB_USER", "{connection['username']}");
    static final String PASSWORD = System.getenv("ORBIT_DB_PASSWORD"); // never hardcoded

    static final Map<String, String> ORBIT_TABLE_MAP = new HashMap<>() {{{{
{table_map}
    }}}};

    public static List<Document> readCollection(String entityKey, int limit) {{
        String collectionName = ORBIT_TABLE_MAP.get(entityKey);
        if (collectionName == null) throw new IllegalArgumentException("No collection mapped for " + entityKey);

        String auth = USER != null && !USER.isEmpty() ? USER + ":" + PASSWORD + "@" : "";
        String uri = "mongodb://" + auth + HOST + ":" + PORT;
        try (MongoClient client = MongoClients.create(uri)) {{
            MongoCollection<Document> collection = client.getDatabase(DATABASE).getCollection(collectionName);
            List<Document> results = new ArrayList<>();
            collection.find().limit(limit).into(results);
            return results;
        }}
    }}
{_java_http_entrypoint("readCollection(entity, limit)")}
}}
"""

    ssl_suffix = "?sslmode=require" if database == "postgresql" and connection["ssl"] else (
        "?useSSL=true" if database == "mysql" and connection["ssl"] else (
            ";encrypt=true" if database == "sqlserver" and connection["ssl"] else ""
        )
    )
    driver_class = _JAVA_DRIVER_CLASS[database]
    jdbc_url_expr = _JAVA_JDBC_EXPR[database].format(ssl=ssl_suffix)
    q, qc = _JAVA_QUOTE[database], _JAVA_QUOTE_CLOSE[database]
    if database == "sqlserver":
        select_expr = f'"SELECT TOP " + limit + " * FROM {q}" + table + "{qc}"'
    else:
        select_expr = f'"SELECT * FROM {q}" + table + "{qc} LIMIT " + limit'

    return f"""/**
 * Orbit Connector - {database}
 * {_install_note("java", database)}
 *
 * Edit ORBIT_TABLE_MAP to point each Orbit entity at your real table
 * name. The password is read only from the environment - it is never
 * written into this file.
 */
import java.sql.*;
import java.util.*;

public class OrbitConnector {{
    static final String HOST = System.getenv().getOrDefault("ORBIT_DB_HOST", "{connection['host']}");
    static final int PORT = Integer.parseInt(System.getenv().getOrDefault("ORBIT_DB_PORT", "{connection['port']}"));
    static final String DATABASE = System.getenv().getOrDefault("ORBIT_DB_NAME", "{connection['database']}");
    static final String USER = System.getenv().getOrDefault("ORBIT_DB_USER", "{connection['username']}");
    static final String PASSWORD = System.getenv("ORBIT_DB_PASSWORD"); // never hardcoded

    // Map each Orbit entity -> your real table name.
    // Leave an entry out if you don't have that table.
    static final Map<String, String> ORBIT_TABLE_MAP = new HashMap<>() {{{{
{table_map}
    }}}};

    static Connection connect() throws Exception {{
        Class.forName("{driver_class}");
        // Built from HOST/PORT/DATABASE every time this runs - edit those
        // fields above, not this line, if your connection details change.
        String url = {jdbc_url_expr};
        return DriverManager.getConnection(url, USER, PASSWORD);
    }}

    public static List<Map<String, Object>> readTable(String entityKey, int limit) throws Exception {{
        String table = ORBIT_TABLE_MAP.get(entityKey);
        if (table == null) throw new IllegalArgumentException("No table mapped for " + entityKey);

        try (Connection conn = connect();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery({select_expr})) {{
            ResultSetMetaData meta = rs.getMetaData();
            List<Map<String, Object>> rows = new ArrayList<>();
            while (rs.next()) {{
                Map<String, Object> row = new LinkedHashMap<>();
                for (int i = 1; i <= meta.getColumnCount(); i++) {{
                    row.put(meta.getColumnName(i), rs.getObject(i));
                }}
                rows.add(row);
            }}
            return rows;
        }}
    }}
{_java_http_entrypoint("readTable(entity, limit)")}
}}
"""


_RENDERERS = {
    "javascript": _javascript,
    "php": _php,
    "python": _python,
    "java": _java,
}


def _install_note(language: str, database: str) -> str:
    if database == "mongodb":
        notes = {
            "javascript": "npm install mongodb",
            "php": "composer require mongodb/mongodb (+ the mongodb PECL extension)",
            "python": "pip install pymongo",
            "java": "Add the MongoDB Java driver (org.mongodb:mongodb-driver-sync) to your build",
        }
        return notes[language]
    if language == "javascript":
        return _JS_DB[database]["install"]
    if language == "python":
        return _PY_DB[database]["install"]
    if language == "php":
        notes = {
            "postgresql": "Requires the PDO_PGSQL extension",
            "mysql": "Requires the PDO_MYSQL extension",
            "sqlserver": "Requires the PDO_SQLSRV extension (Microsoft Drivers for PHP for SQL Server)",
            "sqlite": "Requires the PDO_SQLITE extension",
        }
        return notes[database]
    if language == "java":
        notes = {
            "postgresql": "Add org.postgresql:postgresql to your build",
            "mysql": "Add mysql:mysql-connector-java to your build",
            "sqlserver": "Add com.microsoft.sqlserver:mssql-jdbc to your build",
            "sqlite": "Add org.xerial:sqlite-jdbc to your build",
        }
        return notes[database]
    return ""


def render(language: str, database: str, connection: dict | None, tables: list[dict] | None, filename: str | None) -> tuple[str, str]:
    """
    Returns (code, resolved_filename). Raises ConnectorValidationError for
    an unsupported language/database - the caller (Workflow Engine) turns
    that into a 422, same contract as the SDK Generator's render().
    """
    if language not in CONNECTOR_LANGUAGES:
        raise ConnectorValidationError(
            f"Unsupported language '{language}' - choose one of {CONNECTOR_LANGUAGES}"
        )
    if database not in CONNECTOR_DATABASES:
        raise ConnectorValidationError(
            f"Unsupported database '{database}' - choose one of {CONNECTOR_DATABASES}"
        )

    clean_connection = _clean_connection(database, connection)
    clean_tables = _clean_tables(tables)
    code = _RENDERERS[language](database, clean_connection, clean_tables)
    resolved_filename = resolve_filename(language, filename)
    return code, resolved_filename
