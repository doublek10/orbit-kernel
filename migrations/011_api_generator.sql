-- Orbit Kernel - Orbit API Generator
--
-- One "Company Endpoint" identity per company: a unique slug (the
-- endpoint URL), an HMAC signing secret (encrypted at rest, same as
-- every other credential the Blueprint stores), and a rate limit. The
-- Company Owner requests this once; api-key issuance reuses the
-- existing api_keys table (004_developer.sql) rather than duplicating
-- it - this table only owns what's specific to the endpoint itself.

create table if not exists company_endpoints (
    company_id uuid primary key references companies(id) on delete cascade,
    endpoint_slug text not null unique,
    webhook_secret_encrypted text not null,
    rate_limit_per_minute integer not null default 60,
    created_at timestamptz not null default now(),
    rotated_at timestamptz
);
