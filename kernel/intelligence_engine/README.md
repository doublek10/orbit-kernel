# Intelligence Engine

The autonomous reasoning engine of the Orbit Platform, per
`docs/orbit-intelligence-engine-spec.md` (the engineering spec this
module implements). Owned entirely by the Kernel - the Frontend only
displays what this produces, the Gateway only forwards requests to it.

## Module map

| File | Spec section it implements |
|---|---|
| `manager.py` | Intelligence Manager - lifecycle + the front door every other module calls through |
| `context_builder.py` | "builds an execution context" for background (non-user) work |
| `observer.py` | Event Observation - subscribes to every completed workflow |
| `reasoning_engine.py` | Composition root for one Intelligence Cycle |
| `analysis_engine.py` | Continuous Analysis (trend, spend, anomalies) |
| `health_engine.py` | Business Health |
| `forecasting_engine.py` | Forecasting |
| `recommendation_engine.py` | Recommendations - advice only, never actions |
| `relationship_engine.py` + `knowledge_graph.py` | Knowledge Graph |
| `report_generator.py` | Reports |
| `notification_engine.py` | Notifications |
| `metrics.py` | Intelligence Database - Trend History |
| `cache_manager.py` | Dashboard read caching (implementation detail, not in the spec) |
| `scheduler.py` | Scheduling |
| `models.py` | Shared dataclasses |

## What's real today vs. what's honestly deferred

Real: the full cycle runs end to end - Blueprint publish activates a
company, the Observer/Scheduler trigger cycles, Analysis/Health/
Forecasting produce Findings, Recommendations and Notifications get
persisted and deduped, Reports get generated and stored, the Knowledge
Graph gets rebuilt from the Financial Graph, and every Frontend-facing
read (`dashboard`, `reports`, `notifications`, `forecast`, `performance`,
`knowledge`, `history`, `status`, `preferences`) is wired through
`kernel/workflow_engine/engine.py` exactly like every other capability.

Deferred, honestly: the spec's full Continuous Analysis list (inventory,
payroll, supplier performance, department performance) needs a connected
Business System actually producing that data - `providers/` and
`kernel/integration_manager/` don't have a live adapter for those yet
(see their own READMEs). `observer.py` already subscribes to those event
names; nothing fabricates numbers in the meantime. Deterministic
statistics only, per Intelligence Rule #7 - no LLM call is wired up
(same choice `ai/insights.py` made, which this module supersedes; that
file can be retired once `ai.list` is repointed at
`intelligence_performance.list`).

## Rules this module actually enforces in code

1. `IntelligenceManager.is_active()` is checked before every cycle - Rule #1/#4.
2. Activation only happens from a `blueprint.published` event - Rule #2.
3. Nothing here calls `ProviderManager`, `WorkflowAutomation`, or writes
   to `ledger_transactions` / `provider_connections` - only reads them.
   Rule #9/#10.
4. No randomness anywhere in `analysis_engine.py` / `forecasting_engine.py`
   / `health_engine.py` - Rule #7.
