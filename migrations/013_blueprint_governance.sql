-- Orbit Kernel - Blueprint Governance
--
-- Closes a real gap: the spec says "Everything outside the Blueprint is
-- forbidden" and the Blueprint defines "Allowed Entities... Allowed
-- Questions... Business Rules" - but the original company_blueprints
-- table (006_blueprint.sql) only carried business_type/priorities/one
-- notification threshold. That's personalization, not governance: it
-- steers attention, it doesn't restrict anything.
--
-- These two columns make the Intelligence Engine's Blueprint control
-- real and enforceable (see kernel/intelligence_engine/reasoning_engine.py,
-- analysis_engine.py, relationship_engine.py):
--
--   enabled_capabilities - which kinds of finding the Engine is allowed
--     to surface at all (spec's "Allowed Questions"). NULL/empty means
--     every existing capability is enabled - publishing a Blueprint
--     without an opinion here doesn't silently turn Intelligence off.
--
--   allowed_categories - which ledger categories the Engine is allowed
--     to name in category-specific analysis and the Knowledge Graph
--     (spec's "Allowed Entities" / "Available Fields"). NULL means
--     unrestricted. This does NOT restrict the overall balance, health
--     score, or cash-flow trend - those describe the whole business and
--     stay visible regardless, the same way a redacted expense report
--     still shows the bottom line.

alter table company_blueprints
    add column if not exists enabled_capabilities jsonb not null default '["health","trend","spend","anomaly","forecast"]'::jsonb,
    add column if not exists allowed_categories jsonb;  -- null = unrestricted; else a jsonb array of category strings
