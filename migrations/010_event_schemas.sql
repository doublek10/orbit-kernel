-- Orbit Kernel - Event Schema Builder
--
-- Lets a company declare its own event types (payment.received,
-- invoice.created, ...) with required/optional fields and validation
-- rules. The Schema Engine (kernel/company_blueprint/schema_engine.py)
-- validates incoming events against these and rejects invalid payloads.
-- Versioned like everything else the Blueprint owns - each save creates
-- a new immutable version, the active schema just points at the latest.

create table if not exists event_schemas (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    event_name text not null,                 -- e.g. "payment.received"
    description text not null default '',
    required_fields jsonb not null default '[]'::jsonb,   -- ["amount", "currency"]
    optional_fields jsonb not null default '[]'::jsonb,
    validation_rules jsonb not null default '[]'::jsonb,  -- [{"field": "amount", "type": "number", "min": 0}]
    version integer not null default 1,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (company_id, event_name)
);

create table if not exists event_schema_versions (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    event_name text not null,
    version integer not null,
    snapshot jsonb not null,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now()
);

create index if not exists idx_event_schemas_company on event_schemas(company_id);
create index if not exists idx_event_schema_versions_lookup
    on event_schema_versions(company_id, event_name, version desc);
