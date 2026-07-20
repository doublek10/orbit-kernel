"""
Mapping Engine (Transformation Engine)

Company JSON -> Orbit Canonical Event -> Workflow Engine.

A "mapping" is just a list of {source, target} rules, where `source` is
a dot-notation path into whatever JSON shape a company's own systems
send (e.g. "customer.name", "totalAmount") and `target` is one of
Orbit's canonical event fields. Applying a mapping to a payload is pure,
stateless, and has nothing to do with storage - MappingStore below is
the only piece that touches Postgres.

This keeps the promise in the spec: "The Kernel never changes because
customer payloads change. Only mappings change." - this file is
intentionally payload-shape-agnostic.
"""

import json
from dataclasses import dataclass
from typing import Any

import asyncpg

# The canonical fields a mapping can target - deliberately the same
# vocabulary record_transaction() already uses, so a well-formed mapping
# output can flow straight into the Financial Graph.
CANONICAL_FIELDS = [
    "reference",
    "customer",
    "amount",
    "direction",
    "currency",
    "description",
    "counterparty",
    "category",
    "occurred_at",
]


class MappingValidationError(ValueError):
    pass


def get_nested(payload: dict, dotted_path: str) -> tuple[Any, bool]:
    """Returns (value, found) - `found` is False (not None) when the
    path genuinely doesn't resolve, so a mapped field that's legitimately
    null downstream isn't confused with a missing source field."""
    current: Any = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None, False
    return current, True


def flatten_keys(payload: dict, prefix: str = "") -> list[str]:
    """Dot-notation paths for every leaf (or array) value in a JSON
    object - what the frontend's draggable "source fields" list is
    built from server-side, so the same flattening logic backs both the
    picker and the eventual apply_mapping() call."""
    keys: list[str] = []
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and value:
            keys.extend(flatten_keys(value, path))
        else:
            keys.append(path)
    return keys


def validate_field_rules(field_rules: list[dict]) -> list[dict]:
    if not isinstance(field_rules, list):
        raise MappingValidationError("field_rules must be a list")

    clean = []
    seen_targets = set()
    for rule in field_rules:
        source = (rule.get("source") or "").strip() if isinstance(rule, dict) else ""
        target = (rule.get("target") or "").strip() if isinstance(rule, dict) else ""
        if not source or not target:
            raise MappingValidationError("each rule needs both a source and a target field")
        if target not in CANONICAL_FIELDS:
            raise MappingValidationError(
                f"'{target}' is not a canonical field - choose one of {CANONICAL_FIELDS}"
            )
        if target in seen_targets:
            raise MappingValidationError(f"target field '{target}' is mapped more than once")
        seen_targets.add(target)
        clean.append({"source": source, "target": target})
    return clean


def apply_mapping(payload: dict, field_rules: list[dict]) -> dict:
    canonical: dict[str, Any] = {}
    warnings: list[str] = []
    for rule in field_rules:
        value, found = get_nested(payload, rule["source"])
        if found:
            canonical[rule["target"]] = value
        else:
            warnings.append(f"Source field '{rule['source']}' was not found in the payload")
    return {"canonical": canonical, "warnings": warnings}


@dataclass(frozen=True)
class DataMapping:
    id: str
    name: str
    field_rules: list[dict]
    sample_payload: dict
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "field_rules": self.field_rules,
            "sample_payload": self.sample_payload,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _row_to_mapping(row) -> DataMapping:
    field_rules = row["field_rules"]
    if isinstance(field_rules, str):
        field_rules = json.loads(field_rules)
    sample_payload = row["sample_payload"]
    if isinstance(sample_payload, str):
        sample_payload = json.loads(sample_payload)
    return DataMapping(
        id=str(row["id"]),
        name=row["name"],
        field_rules=list(field_rules or []),
        sample_payload=dict(sample_payload or {}),
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


class MappingStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def list_mappings(self, company_id: str) -> list[DataMapping]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM data_mappings WHERE company_id = $1 ORDER BY updated_at DESC",
                company_id,
            )
        return [_row_to_mapping(r) for r in rows]

    async def get(self, company_id: str, mapping_id: str) -> DataMapping | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM data_mappings WHERE id = $1 AND company_id = $2",
                mapping_id,
                company_id,
            )
        return _row_to_mapping(row) if row else None

    async def upsert(
        self, *, company_id: str, created_by: str, name: str, field_rules: list[dict], sample_payload: dict
    ) -> DataMapping:
        name = (name or "").strip()
        if not name:
            raise MappingValidationError("name is required")
        clean_rules = validate_field_rules(field_rules)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO data_mappings (company_id, name, field_rules, sample_payload, created_by)
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
                ON CONFLICT (company_id, name) DO UPDATE SET
                    field_rules = EXCLUDED.field_rules,
                    sample_payload = EXCLUDED.sample_payload,
                    updated_at = now()
                RETURNING *
                """,
                company_id,
                name,
                clean_rules,
                sample_payload or {},
                created_by,
            )
        return _row_to_mapping(row)

    async def delete(self, company_id: str, mapping_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM data_mappings WHERE id = $1 AND company_id = $2",
                mapping_id,
                company_id,
            )
        return result.endswith("1")
