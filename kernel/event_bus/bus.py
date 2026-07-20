"""
Event Bus

Every completed workflow publishes an event here (Development Rule #7).
This is the in-process pub/sub implementation; swap for Postgres
LISTEN/NOTIFY, Redis Streams, or NATS once there's more than one process
consuming events. Every published event is also persisted to the
`events` table so the Replay module and audit trail have a durable log
to work from, independent of whether anything is subscribed right now.
"""

from collections import defaultdict
from typing import Awaitable, Callable

import asyncpg


class EventBus:
    def __init__(self, pool: asyncpg.Pool | None = None):
        self._pool = pool
        self._subscribers: dict[str, list[Callable[[dict, str | None], Awaitable[None]]]] = (
            defaultdict(list)
        )

    def subscribe(self, event_name: str, handler: Callable[[dict, str | None], Awaitable[None]]) -> None:
        """
        `handler(payload, company_id)` - company_id is passed alongside
        the payload (not merged into it) since it's metadata about the
        event, not part of it; the Intelligence Observer is the first
        subscriber that actually needs it, to know which company's
        Intelligence Cycle to run.
        """
        self._subscribers[event_name].append(handler)

    async def publish(self, event_name: str, payload: dict, company_id: str | None = None) -> None:
        if self._pool is not None:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO events (company_id, event_name, payload)
                    VALUES ($1, $2, $3::jsonb)
                    """,
                    company_id,
                    event_name,
                    payload,
                )

        for handler in self._subscribers.get(event_name, []):
            await handler(payload, company_id)


_bus: EventBus | None = None


def get_event_bus(pool: asyncpg.Pool) -> EventBus:
    """
    Process-wide Event Bus singleton. A fresh `EventBus(pool)` per request
    (the old pattern) is fine for *publishing* - every event still lands
    in the `events` table - but it silently drops every `subscribe()`,
    since a new instance means a new, empty `_subscribers` dict. That
    made Development Rule #7 ("every completed workflow publishes
    events") true but left nothing in-process actually listening.

    The Intelligence Engine's Observer needs a real, standing
    subscription (spec: "The Intelligence Engine subscribes to every
    completed workflow"), so callers that need subscriptions to survive
    across requests - the Observer at startup, the Workflow Engine at
    every publish - should share this one instance instead of
    constructing their own.
    """
    global _bus
    if _bus is None:
        _bus = EventBus(pool)
    return _bus
