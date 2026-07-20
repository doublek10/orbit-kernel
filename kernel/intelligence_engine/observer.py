"""
Intelligence Engine - Observer

"The Intelligence Engine subscribes to every completed workflow" (spec).
Subscribes to the shared Event Bus (kernel.event_bus.bus.get_event_bus)
at Kernel startup - see main.py - for the event names the spec's Event
Observation section lists, plus `blueprint.published`, which is what
actually activates the Engine for a company per the Intelligence
Lifecycle. This module only owns *which* events matter - what running a
cycle actually does lives in IntelligenceManager.on_event.
"""

import logging

import asyncpg

from kernel.event_bus.bus import EventBus
from kernel.intelligence_engine.manager import get_intelligence_manager

logger = logging.getLogger(__name__)

# Spec's Event Observation examples, translated to this codebase's actual
# event names (see kernel/workflow_engine/engine.py's `_events.publish`
# call sites). Events for systems not built yet (payroll, inventory,
# purchasing) are included so the Observer is already wired the moment
# those Business Systems start publishing them - subscribing to an event
# nothing publishes yet is simply a subscription that never fires.
OBSERVED_EVENTS = (
    "transaction.recorded",
    "ledger.csv_imported",
    "provider.connected",
    "provider.disconnected",
    "integration.connected",
    "integration.disconnected",
    "blueprint.published",
    "blueprint.version_restored",
    "workflow.created",
    "mapping.saved",
    "schema.saved",
    "replay.simulated",
    # Not yet emitted by any Workflow Engine handler - reserved so the
    # Observer needs no code change once payroll/inventory/purchasing
    # workflows exist.
    "payment.received",
    "invoice.created",
    "invoice.paid",
    "inventory.updated",
    "payroll.completed",
    "expense.recorded",
    "supplier.updated",
    "customer.registered",
    "order.completed",
    "purchase.created",
    "tax.filed",
    "refund.issued",
)


def subscribe_observer(pool: asyncpg.Pool, bus: EventBus) -> None:
    manager = get_intelligence_manager(pool)

    def make_handler(event_name: str):
        async def handler(payload: dict, company_id: str | None) -> None:
            if company_id is None:
                # Events published without a company scope (none exist
                # today) aren't Intelligence's concern - it only ever
                # observes per-company activity, per the Blueprint
                # boundary.
                return
            try:
                await manager.on_event(event_name, payload, company_id)
            except Exception:  # noqa: BLE001
                # An Intelligence hiccup must never break the workflow
                # that triggered it - the Engine only observes, it never
                # blocks business execution (spec's Design Philosophy).
                logger.exception(
                    "Intelligence Observer failed handling '%s' for company %s", event_name, company_id
                )

        return handler

    for event_name in OBSERVED_EVENTS:
        bus.subscribe(event_name, make_handler(event_name))
