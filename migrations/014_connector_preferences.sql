-- Orbit Kernel - Connector Generator preferences
--
-- Remembers what a company last used in the Connector Generator wizard
-- so they don't have to re-pick it every visit: the language ("code
-- extension" - javascript/php/python/java), the database engine, and
-- the deployed Connector URL (see connector_generator.py's HTTP
-- entrypoints / connector_tester.py's _test_via_url). One row per
-- company, same upsert-on-write shape as intelligence_preferences
-- (012_intelligence.sql).
--
-- Deliberately narrow, matching the Connector Generator's existing
-- non-negotiable: host/port/database name/username are fine to prefill
-- from a copy-pasted sample, but a password is NEVER persisted here or
-- anywhere else - only what's safe to keep around is remembered.

create table if not exists connector_preferences (
    company_id uuid primary key references companies(id) on delete cascade,
    language text not null,
    database_engine text not null,
    connector_url text,
    updated_at timestamptz not null default now()
);
