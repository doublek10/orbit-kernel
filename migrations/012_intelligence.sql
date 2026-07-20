-- Orbit Kernel - Intelligence Engine
--
-- Backs kernel/intelligence_engine/*. Per the spec: "Orbit stores only
-- derived intelligence, metrics, knowledge, and audit information" -
-- raw company operational data stays in ledger_transactions /
-- provider_connections / etc. (financial_graph, provider_manager).
-- Nothing here is a source of truth for money; it's all reproducible
-- from those tables plus the active Company Blueprint.

-- Lifecycle: one row per company, created the instant a Blueprint is
-- first published, per "Intelligence Engine Activated" in the spec's
-- Intelligence Lifecycle. `active` flips off if the company disables
-- Intelligence or the account is closed - the Engine never runs for a
-- company that isn't active.
create table if not exists intelligence_status (
    company_id uuid primary key references companies(id) on delete cascade,
    active boolean not null default false,
    activated_at timestamptz,
    deactivated_at timestamptz,
    blueprint_version integer,
    last_event_at timestamptz,
    last_cycle_at timestamptz
);

-- One row per background job per company, so the Scheduler knows what's
-- due without guessing - "Every Hour: Business Health", "Every Day:
-- Daily Summary", etc. from the spec's Scheduling section.
create table if not exists intelligence_job_runs (
    company_id uuid not null references companies(id) on delete cascade,
    job_name text not null,          -- health_hourly | daily_summary | weekly_executive | monthly_forecast | quarterly_trend
    last_run_at timestamptz not null default now(),
    primary key (company_id, job_name)
);

-- Trend History: numbered metric snapshots, so "Business health improved
-- 12% since last week" is a real query over stored history, not a
-- recomputation that could silently change if ledger data is edited.
create table if not exists intelligence_metrics (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    metric_key text not null,        -- e.g. 'health_score', 'net_cash_flow_30d'
    value numeric not null,
    context jsonb not null default '{}'::jsonb,
    computed_at timestamptz not null default now()
);
create index if not exists idx_intelligence_metrics_lookup
    on intelligence_metrics(company_id, metric_key, computed_at desc);

-- Knowledge Graph: nodes are business entities the Blueprint's business
-- type surfaces from the Financial Graph today (categories, counter-
-- parties, accounts) - not a generic graph DB, just enough structure to
-- answer "what does this business's money touch, and how".
create table if not exists intelligence_knowledge_nodes (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    entity_type text not null,       -- category | counterparty | account
    entity_key text not null,
    attributes jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now(),
    unique (company_id, entity_type, entity_key)
);

create table if not exists intelligence_knowledge_edges (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    from_type text not null,
    from_key text not null,
    relationship text not null,      -- flows_into | flows_from | largest_counterparty_of
    to_type text not null,
    to_key text not null,
    weight numeric not null default 0,
    updated_at timestamptz not null default now(),
    unique (company_id, from_type, from_key, relationship, to_type, to_key)
);
create index if not exists idx_intelligence_edges_company on intelligence_knowledge_edges(company_id);

create table if not exists intelligence_reports (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    report_type text not null,       -- daily_summary | weekly_executive | monthly_forecast | quarterly_trend
    period_start timestamptz not null,
    period_end timestamptz not null,
    data jsonb not null,
    generated_at timestamptz not null default now()
);
create index if not exists idx_intelligence_reports_lookup
    on intelligence_reports(company_id, report_type, generated_at desc);

create table if not exists intelligence_notifications (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    category text not null,          -- health | cash_flow | risk | forecast | growth
    severity text not null,          -- info | warning | critical
    title text not null,
    message text not null,
    data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    read_at timestamptz
);
create index if not exists idx_intelligence_notifications_lookup
    on intelligence_notifications(company_id, created_at desc);

create table if not exists intelligence_recommendations (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    rec_type text not null,
    title text not null,
    message text not null,
    data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    dismissed_at timestamptz
);
create index if not exists idx_intelligence_recommendations_lookup
    on intelligence_recommendations(company_id, created_at desc);

-- "Notifications are sent according to company preferences" - one row
-- per company, editable via intelligence_preferences.create (POST
-- /api/intelligence/preferences and PUT /api/intelligence/settings both
-- write here; see kernel/intelligence_engine/manager.py).
create table if not exists intelligence_preferences (
    company_id uuid primary key references companies(id) on delete cascade,
    daily_summary boolean not null default true,
    weekly_executive boolean not null default true,
    monthly_forecast boolean not null default true,
    min_notification_severity text not null default 'info',  -- info | warning | critical
    updated_at timestamptz not null default now()
);
