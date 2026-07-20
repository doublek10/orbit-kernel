-- Orbit Kernel - workflow automation
--
-- Backs the Workflow Engine's "workflows.create" capability: companies
-- can define simple trigger -> condition -> action automations that run
-- synchronously whenever their trigger event fires (currently only
-- 'transaction.recorded', emitted by the Financial Graph on every new
-- ledger entry). This is intentionally the simplest real implementation
-- that could work - swap the synchronous evaluation for a queue-backed
-- worker later without changing the schema or the API shape.

create table if not exists workflow_definitions (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    name text not null,
    trigger_event text not null,           -- e.g. 'transaction.recorded'
    condition jsonb not null default '{}'::jsonb,  -- {field, op, value}
    action jsonb not null default '{}'::jsonb,     -- {type, ...}
    enabled boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists automation_runs (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    workflow_id uuid not null references workflow_definitions(id) on delete cascade,
    trigger_event text not null,
    matched_payload jsonb not null default '{}'::jsonb,
    action_result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_workflow_defs_company on workflow_definitions(company_id, trigger_event);
create index if not exists idx_automation_runs_company on automation_runs(company_id, created_at desc);
