-- Orbit Kernel - developer platform (API keys)
--
-- Backs the Developer page's key management. Only the hash is ever
-- stored - the plaintext key is returned exactly once, at creation time,
-- same as every real API key system (Stripe, GitHub tokens, etc).

create table if not exists api_keys (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    name text not null,
    key_prefix text not null,      -- first 8 chars, shown in the UI for identification
    key_hash text not null,        -- sha256 of the full key, never the key itself
    created_by uuid references users(id) on delete set null,
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    revoked boolean not null default false
);

create index if not exists idx_api_keys_company on api_keys(company_id);
