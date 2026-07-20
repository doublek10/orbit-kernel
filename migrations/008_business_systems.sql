-- Orbit Kernel - Business Systems
--
-- The Blueprint's "Business Systems" section: payroll, accounting,
-- inventory, CRM, ERP, warehouse, POS, HR, and custom systems - distinct
-- from Financial Connections (provider_connections). Each row is one
-- connection a company has told Orbit about; the spec's required display
-- fields (Provider, Status, Last Sync, Authentication, Health,
-- Connection ID) map directly onto these columns.

create table if not exists business_system_connections (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    provider text not null,             -- catalog slug, e.g. 'quickbooks'
    display_name text not null,
    system_type text not null,          -- payroll | accounting | inventory | crm | erp | warehouse | pos | hr | custom
    status text not null default 'connected',
    health text not null default 'unknown',   -- unknown | healthy | unhealthy
    auth_method text not null default 'api_key',
    credentials_encrypted jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    connected_at timestamptz not null default now(),
    last_synced_at timestamptz,
    disconnected_at timestamptz,
    unique (company_id, provider)
);

create index if not exists idx_business_systems_company on business_system_connections(company_id);
