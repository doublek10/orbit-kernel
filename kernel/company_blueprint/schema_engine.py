"""
Schema Engine

Validates incoming events, rejects invalid payloads, supports schema
versioning - the spec's Event Schema Builder made real. A company
declares its own event types (payment.received, invoice.created, ...)
with required/optional fields and validation rules; this module stores
those declarations and checks arbitrary payloads against them.

Deliberately permissive about unknown fields (returned as warnings, not
errors) - a schema exists to catch missing or malformed data, not to
reject forward-compatible payloads that carry an extra field.
"""

import json
from dataclasses import dataclass
from typing import Any

import asyncpg

VALID_RULE_TYPES = {"string", "number", "boolean"}


class SchemaValidationError(ValueError):
    """Raised for a malformed schema *definition* (not a payload that fails it)."""


def validate_schema_input(payload: dict) -> dict:
    event_name = (payload.get("event_name") or "").strip()
    if not event_name:
        raise SchemaValidationError("event_name is required")

    required_fields = payload.get("required_fields") or []
    optional_fields = payload.get("optional_fields") or []
    if not isinstance(required_fields, list) or not all(isinstance(f, str) for f in required_fields):
        raise SchemaValidationError("required_fields must be a list of field names")
    if not isinstance(optional_fields, list) or not all(isinstance(f, str) for f in optional_fields):
        raise SchemaValidationError("optional_fields must be a list of field names")

    overlap = set(required_fields) & set(optional_fields)
    if overlap:
        raise SchemaValidationError(f"fields can't be both required and optional: {sorted(overlap)}")

    validation_rules = payload.get("validation_rules") or []
    if not isinstance(validation_rules, list):
        raise SchemaValidationError("validation_rules must be a list")

    clean_rules = []
    known_fields = set(required_fields) | set(optional_fields)
    for rule in validation_rules:
        if not isinstance(rule, dict):
            raise SchemaValidationError("each validation rule must be an object")
        field = (rule.get("field") or "").strip()
        rule_type = rule.get("type")
        if not field or field not in known_fields:
            raise SchemaValidationError(
                f"validation rule field '{field}' must be one of the schema's declared fields"
            )
        if rule_type not in VALID_RULE_TYPES:
            raise SchemaValidationError(f"rule type must be one of {sorted(VALID_RULE_TYPES)}")
        clean = {"field": field, "type": rule_type}
        if "min" in rule and rule["min"] is not None:
            clean["min"] = float(rule["min"])
        if "max" in rule and rule["max"] is not None:
            clean["max"] = float(rule["max"])
        if "enum" in rule and rule["enum"]:
            clean["enum"] = list(rule["enum"])
        clean_rules.append(clean)

    return {
        "event_name": event_name,
        "description": (payload.get("description") or "").strip(),
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "validation_rules": clean_rules,
    }


def validate_event(payload: dict, schema: "EventSchema") -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for field in schema.required_fields:
        if field not in payload:
            errors.append(f"missing required field '{field}'")

    known_fields = set(schema.required_fields) | set(schema.optional_fields)
    for field in payload:
        if field not in known_fields:
            warnings.append(f"'{field}' is not declared on this schema")

    for rule in schema.validation_rules:
        field = rule["field"]
        if field not in payload:
            continue
        value = payload[field]
        expected = rule["type"]

        type_ok = (
            (expected == "string" and isinstance(value, str))
            or (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (expected == "boolean" and isinstance(value, bool))
        )
        if not type_ok:
            errors.append(f"'{field}' must be a {expected}")
            continue

        if expected == "number":
            if "min" in rule and value < rule["min"]:
                errors.append(f"'{field}' must be >= {rule['min']}")
            if "max" in rule and value > rule["max"]:
                errors.append(f"'{field}' must be <= {rule['max']}")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"'{field}' must be one of {rule['enum']}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


@dataclass(frozen=True)
class EventSchema:
    id: str
    event_name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]
    validation_rules: list[dict]
    version: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_name": self.event_name,
            "description": self.description,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "validation_rules": self.validation_rules,
            "version": self.version,
            "updated_at": self.updated_at,
        }


def _row_to_schema(row) -> EventSchema:
    def _jsonb(value):
        return json.loads(value) if isinstance(value, str) else value

    return EventSchema(
        id=str(row["id"]),
        event_name=row["event_name"],
        description=row["description"],
        required_fields=list(_jsonb(row["required_fields"]) or []),
        optional_fields=list(_jsonb(row["optional_fields"]) or []),
        validation_rules=list(_jsonb(row["validation_rules"]) or []),
        version=row["version"],
        updated_at=row["updated_at"].isoformat(),
    )


class SchemaStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def list_schemas(self, company_id: str) -> list[EventSchema]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM event_schemas WHERE company_id = $1 ORDER BY updated_at DESC",
                company_id,
            )
        return [_row_to_schema(r) for r in rows]

    async def get(self, company_id: str, schema_id: str) -> EventSchema | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM event_schemas WHERE id = $1 AND company_id = $2",
                schema_id,
                company_id,
            )
        return _row_to_schema(row) if row else None

    async def upsert(self, *, company_id: str, created_by: str, payload: dict) -> EventSchema:
        clean = validate_schema_input(payload)

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO event_schemas
                        (company_id, event_name, description, required_fields, optional_fields,
                         validation_rules, version, created_by, updated_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, 1, $7, now())
                    ON CONFLICT (company_id, event_name) DO UPDATE SET
                        description = EXCLUDED.description,
                        required_fields = EXCLUDED.required_fields,
                        optional_fields = EXCLUDED.optional_fields,
                        validation_rules = EXCLUDED.validation_rules,
                        version = event_schemas.version + 1,
                        updated_at = now()
                    RETURNING *
                    """,
                    company_id,
                    clean["event_name"],
                    clean["description"],
                    clean["required_fields"],
                    clean["optional_fields"],
                    clean["validation_rules"],
                    created_by,
                )
                schema = _row_to_schema(row)

                await conn.execute(
                    """
                    INSERT INTO event_schema_versions (company_id, event_name, version, snapshot, created_by)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    company_id,
                    schema.event_name,
                    schema.version,
                    schema.to_dict(),
                    created_by,
                )
        return schema

    async def delete(self, company_id: str, schema_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM event_schemas WHERE id = $1 AND company_id = $2", schema_id, company_id
            )
        return result.endswith("1")

    async def versions(self, company_id: str, schema_id: str) -> list[dict]:
        schema = await self.get(company_id, schema_id)
        if schema is None:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT esv.version, esv.snapshot, esv.created_at, u.email AS created_by_email
                FROM event_schema_versions esv
                JOIN users u ON u.id = esv.created_by
                WHERE esv.company_id = $1 AND esv.event_name = $2
                ORDER BY esv.version DESC
                """,
                company_id,
                schema.event_name,
            )
        return [
            {
                "version": r["version"],
                "snapshot": json.loads(r["snapshot"]) if isinstance(r["snapshot"], str) else r["snapshot"],
                "created_by_email": r["created_by_email"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
