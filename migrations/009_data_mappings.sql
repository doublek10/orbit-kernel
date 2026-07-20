-- Orbit Kernel - Data Mapping
--
-- The Blueprint's Visual JSON Mapper: a company tells Orbit how the
-- JSON its own systems already send maps onto Orbit's canonical event
-- fields (invoiceNumber -> reference, totalAmount -> amount, ...). The
-- Transformation Engine (kernel/company_blueprint/mapping_engine.py)
-- applies these rules to turn a company's own payload shape into a
-- canonical event - "the Kernel never changes because customer payloads
-- change, only mappings change".

create table if not exists data_mappings (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    name text not null,
    field_rules jsonb not null default '[]'::jsonb,   -- [{"source": "totalAmount", "target": "amount"}, ...]
    sample_payload jsonb not null default '{}'::jsonb, -- last JSON pasted, kept so reopening the mapper isn't blank
    created_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (company_id, name)
);

create index if not exists idx_data_mappings_company on data_mappings(company_id);
