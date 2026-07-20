-- Orbit Kernel - financial core
--
-- Adds the tables the Financial Graph, Provider Manager, and Event Bus
-- need to be real instead of stubs. Every table is scoped by company_id
-- so tenant isolation is enforced at the query layer everywhere above
-- this (Development Rule: the Kernel never returns cross-tenant data).

create table if not exists accounts (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    name text not null,
    currency text not null default 'KES',
    kind text not null default 'wallet',   -- wallet | bank | mobile_money | credit
    created_at timestamptz not null default now(),
    unique (company_id, name)
);

create table if not exists provider_connections (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    provider text not null,                -- adapter name, e.g. 'mock_mobile_money'
    display_name text not null,
    status text not null default 'connected',
    account_id uuid references accounts(id) on delete set null,
    connected_at timestamptz not null default now(),
    last_synced_at timestamptz,
    metadata jsonb not null default '{}'::jsonb
);

create table if not exists ledger_transactions (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    account_id uuid not null references accounts(id) on delete cascade,
    connection_id uuid references provider_connections(id) on delete set null,
    direction text not null check (direction in ('inflow', 'outflow')),
    amount numeric(18, 2) not null check (amount > 0),
    currency text not null default 'KES',
    category text not null default 'uncategorized',
    counterparty text,
    description text not null default '',
    source text not null default 'manual', -- manual | provider_sync
    is_anomaly boolean not null default false,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists events (
    id bigserial primary key,
    company_id uuid references companies(id) on delete cascade,
    event_name text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_accounts_company on accounts(company_id);
create index if not exists idx_connections_company on provider_connections(company_id);
create index if not exists idx_ledger_company_time on ledger_transactions(company_id, occurred_at desc);
create index if not exists idx_ledger_account on ledger_transactions(account_id);
create index if not exists idx_events_company on events(company_id, created_at desc);
