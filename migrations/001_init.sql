-- Orbit Kernel - initial schema
--
-- This lives entirely in the self-hosted Postgres instance (VPN/private
-- network only). Supabase's `auth.users` table is a separate system we do
-- NOT query directly - `users.id` below is just a copy of the Supabase
-- user id (the JWT `sub` claim), kept here so the Kernel can own company
-- membership and permissions without ever touching Supabase's database.

create extension if not exists "pgcrypto";

create table if not exists users (
    id uuid primary key,              -- matches Supabase auth.users.id (UUID returned by Supabase on signup)
    email text not null unique,
    full_name text,
    created_at timestamptz not null default now()
);

create table if not exists companies (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    country text not null,            -- drives which country package loads
    created_at timestamptz not null default now()
);

create table if not exists company_members (
    user_id uuid not null references users(id) on delete cascade,
    company_id uuid not null references companies(id) on delete cascade,
    role text not null default 'member',   -- owner | admin | member | viewer ...
    permissions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    primary key (user_id, company_id)
);

create table if not exists audit_log (
    id bigserial primary key,
    actor_id uuid not null,
    company_id uuid,
    action text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_company_members_user on company_members(user_id);
create index if not exists idx_audit_log_company on audit_log(company_id);
