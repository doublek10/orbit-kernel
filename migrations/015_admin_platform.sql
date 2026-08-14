-- Orbit Kernel - Admin Control Panel schema
--
-- Everything here is exclusively for the internal Admin Control Panel
-- (admin-frontend / admin-gateway). It shares this same self-hosted
-- Postgres instance and the same Kernel process, but is authenticated
-- and authorized completely separately from tenant users:
--   - tenant identity  -> Supabase (see shared/auth/)
--   - admin identity   -> admin_users below, verified with pgcrypto,
--                         never touches Supabase at all.

create extension if not exists "pgcrypto";

-- ── Admin operators ─────────────────────────────────────────────────
-- Password hashing is done entirely in Postgres via pgcrypto's bcrypt
-- (crypt()/gen_salt('bf')) so the Kernel never needs a Python password
-- hashing dependency and never handles a plaintext password outside of
-- a single parameterised query.
create table if not exists admin_users (
    id uuid primary key default gen_random_uuid(),
    username text not null unique,
    password_hash text not null,
    must_change_password boolean not null default true,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    last_login_at timestamptz
);

-- Seed the initial operator account. Safe to re-run - does nothing if
-- the username already exists (e.g. after the admin has changed their
-- password via the panel).
insert into admin_users (username, password_hash, must_change_password)
values ('admin374512', crypt('Admin1234', gen_salt('bf')), true)
on conflict (username) do nothing;

-- ── Tenant deactivation switches ────────────────────────────────────
-- The admin's "deactivate a company / user" power needs somewhere to
-- live. Enforced in kernel/company_resolver/resolver.py on every single
-- request, not just checked at login time.
alter table companies add column if not exists is_active boolean not null default true;
alter table users add column if not exists is_active boolean not null default true;

-- ── Per-company data flow / usage counters ──────────────────────────
-- One row per Kernel /execute call, classified read / write / analysis
-- by kernel/admin/usage_tracker.py. Deliberately a simple event log
-- (not a byte-level profiler) - aggregated into percentages on read for
-- the Admin Overview page.
create table if not exists company_usage_events (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    event_type text not null check (event_type in ('read', 'write', 'analysis')),
    workflow text,
    created_at timestamptz not null default now()
);

create index if not exists idx_usage_events_company_time
    on company_usage_events (company_id, created_at desc);

-- ── Kernel error log ─────────────────────────────────────────────────
-- Every unhandled exception the Kernel raises (its global FastAPI
-- exception handlers in main.py) is recorded here, independent of the
-- ordinary audit_log (which only records successful, intentional
-- actions). This is what backs the Admin "Errors" page.
create table if not exists error_log (
    id bigserial primary key,
    source text not null,             -- e.g. 'kernel.execute', 'kernel.unhandled'
    code text not null,                -- e.g. 'VALUE_ERROR', 'NOT_IMPLEMENTED', exception class name
    message text not null,
    detail jsonb not null default '{}'::jsonb,
    company_id uuid,
    request_path text,
    created_at timestamptz not null default now()
);

create index if not exists idx_error_log_created on error_log (created_at desc);
create index if not exists idx_error_log_code on error_log (code);

-- ── Security alerts ──────────────────────────────────────────────────
-- Distinct from error_log: these are specifically security-relevant
-- events (bad gateway secret, invalid/expired admin session, access
-- attempts against a deactivated company/user, repeated failed admin
-- logins). The Admin Control Panel polls this on every page so an
-- operator sees a new alert no matter where they're currently looking.
create table if not exists security_alerts (
    id bigserial primary key,
    severity text not null check (severity in ('info', 'warning', 'critical')),
    category text not null,
    message text not null,
    company_id uuid,
    source_page text,
    resolved boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_security_alerts_unresolved
    on security_alerts (resolved, created_at desc);
