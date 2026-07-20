-- Orbit Kernel - Financial Connections
--
-- Extends provider_connections (created in 002_financial_core.sql) with
-- the fields the Company Blueprint spec's Financial Connections section
-- collects: category, country, auth method, encrypted credentials,
-- webhook URL, encrypted signing secret, encrypted refresh token.
--
-- Secrets are stored ENCRYPTED (see kernel/company_blueprint/encryption.py)
-- - never plaintext, per Design Principle #6 ("every credential is
-- encrypted before storage").

alter table provider_connections
    add column if not exists category text not null default 'custom',
    add column if not exists country text,
    add column if not exists auth_method text not null default 'api_key',
    add column if not exists credentials_encrypted jsonb not null default '{}'::jsonb,
    add column if not exists webhook_url text,
    add column if not exists signing_secret_encrypted text,
    add column if not exists refresh_token_encrypted text,
    add column if not exists disconnected_at timestamptz;

-- A company can only have one connection per provider slug - connecting
-- again re-activates/updates it rather than creating a duplicate row
-- (the pre-Financial-Connections INSERT relied on an ON CONFLICT clause
-- with no matching constraint, which silently never triggered).
alter table provider_connections
    drop constraint if exists uq_provider_connections_company_provider;
alter table provider_connections
    add constraint uq_provider_connections_company_provider unique (company_id, provider);
