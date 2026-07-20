"""
Workflow Automation

The real implementation behind "workflows.create" - companies define
simple trigger -> condition -> action rules ("when a transaction over
50,000 KES comes in, tag it for review") without writing code. This is
intentionally the simplest version that's actually real: evaluation
happens synchronously, right after the triggering event, in-process.
Swap for a queue-backed worker consuming the Event Bus later - the
schema and public methods here don't need to change for that.

Supported conditions (all operate on a flat payload dict, e.g. a
transaction's to_dict()):
    {"field": "amount", "op": "gt", "value": 50000}
    {"field": "category", "op": "eq", "value": "utilities"}
    {"field": "description", "op": "contains", "value": "supplier"}

Supported actions:
    {"type": "tag", "value": "needs-review"}   -> recorded on the run log
    {"type": "notify", "message": "..."}       -> recorded on the run log
Both are logged to `automation_runs` rather than silently no-op'd, since
there's no notification channel (email/SMS/webhook) wired up yet - that's
honest "planned", not faked.
"""

import json
from dataclasses import dataclass

import asyncpg

_OPS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: float(a) > float(b),
    "gte": lambda a, b: float(a) >= float(b),
    "lt": lambda a, b: float(a) < float(b),
    "lte": lambda a, b: float(a) <= float(b),
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
}


@dataclass(frozen=True)
class WorkflowDefinition:
    id: str
    name: str
    trigger_event: str
    condition: dict
    action: dict
    enabled: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "condition": self.condition,
            "action": self.action,
            "enabled": self.enabled,
        }


class WorkflowAutomation:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def create(
        self, *, company_id: str, name: str, trigger_event: str, condition: dict, action: dict
    ) -> WorkflowDefinition:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_definitions (company_id, name, trigger_event, condition, action)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                RETURNING id, name, trigger_event, condition, action, enabled
                """,
                company_id,
                name,
                trigger_event,
                condition,
                action,
            )
        return self._row_to_definition(row)

    async def list(self, company_id: str) -> list[WorkflowDefinition]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, trigger_event, condition, action, enabled
                FROM workflow_definitions
                WHERE company_id = $1
                ORDER BY created_at DESC
                """,
                company_id,
            )
        return [self._row_to_definition(row) for row in rows]

    async def recent_runs(self, company_id: str, *, limit: int = 20) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ar.id, wd.name AS workflow_name, ar.trigger_event,
                       ar.matched_payload, ar.action_result, ar.created_at
                FROM automation_runs ar
                JOIN workflow_definitions wd ON wd.id = ar.workflow_id
                WHERE ar.company_id = $1
                ORDER BY ar.created_at DESC
                LIMIT $2
                """,
                company_id,
                limit,
            )
        return [
            {
                "id": row["id"],
                "workflow_name": row["workflow_name"],
                "trigger_event": row["trigger_event"],
                "matched_payload": row["matched_payload"],
                "action_result": row["action_result"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    async def evaluate_and_run(self, company_id: str, trigger_event: str, payload: dict) -> list[dict]:
        """Called right after an event happens (e.g. a transaction is
        recorded). Checks every enabled definition for this company and
        trigger, runs the ones whose condition matches, logs the result."""
        definitions = [
            d for d in await self.list(company_id) if d.enabled and d.trigger_event == trigger_event
        ]
        triggered = []
        for definition in definitions:
            if not self._matches(definition.condition, payload):
                continue
            action_result = self._run_action(definition.action, payload)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO automation_runs
                        (company_id, workflow_id, trigger_event, matched_payload, action_result)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                    """,
                    company_id,
                    definition.id,
                    trigger_event,
                    payload,
                    action_result,
                )
            triggered.append({"workflow": definition.name, "action_result": action_result})
        return triggered

    def _matches(self, condition: dict, payload: dict) -> bool:
        if not condition:
            return True
        field, op, value = condition.get("field"), condition.get("op"), condition.get("value")
        if field is None or op not in _OPS or field not in payload:
            return False
        try:
            return _OPS[op](payload[field], value)
        except (TypeError, ValueError):
            return False

    def _run_action(self, action: dict, payload: dict) -> dict:
        action_type = action.get("type", "tag")
        if action_type == "notify":
            return {"type": "notify", "message": action.get("message", "Condition matched")}
        return {"type": "tag", "value": action.get("value", "flagged")}

    @staticmethod
    def _row_to_definition(row) -> WorkflowDefinition:
        return WorkflowDefinition(
            id=str(row["id"]),
            name=row["name"],
            trigger_event=row["trigger_event"],
            condition=row["condition"] if isinstance(row["condition"], dict) else json.loads(row["condition"]),
            action=row["action"] if isinstance(row["action"], dict) else json.loads(row["action"]),
            enabled=row["enabled"],
        )
