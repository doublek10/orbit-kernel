-- Orbit Kernel - Company Blueprint
--
-- Backs the first-login setup wizard: "how do you want Orbit to work for
-- you". This is intentionally the smallest real slice of the full
-- Company Blueprint spec (financial connections + business systems +
-- schema builder + SDK generator are their own, larger build-outs) - but
-- it follows the same Design Principles as the full spec:
--   - every company owns exactly one ACTIVE blueprint (company_blueprints)
--   - every change is versioned and immutable (company_blueprint_versions)
--   - the Blueprint is configuration the Kernel interprets, not logic the
--     Frontend or Gateway understand

create table if not exists company_blueprints (
    company_id uuid primary key references companies(id) on delete cascade,
    business_type text not null,               -- retail | services | agriculture | ...
    priorities jsonb not null default '[]'::jsonb,  -- what the owner cares about most
    large_transaction_threshold numeric,        -- null = no threshold set
    notify_on_large_transaction boolean not null default true,
    weekly_digest boolean not null default true,
    version integer not null default 1,
    published_by uuid not null references users(id),
    published_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists company_blueprint_versions (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    version integer not null,
    snapshot jsonb not null,          -- full blueprint payload at this version
    published_by uuid not null references users(id),
    created_at timestamptz not null default now()
);

create index if not exists idx_blueprint_versions_company
    on company_blueprint_versions(company_id, version desc);
