-- Company subscriptions.
--
-- Deliberately minimal: no plans, no payment processing, no recurring
-- billing integration - just "this company is allowed to operate until
-- this timestamp". An admin grants one from the Admin Control Panel
-- once the company is active; it starts immediately and runs for
-- exactly one calendar month.
--
-- Whether a company even uses this feature is optional: a company with
-- zero rows here is NOT gated by subscription status at all (see the
-- enforcement in kernel/company_resolver/resolver.py) - only a company
-- an admin has explicitly granted at least one subscription to is ever
-- blocked for being expired. This lets the feature be adopted
-- gradually instead of requiring every existing company to be
-- backfilled with a subscription on migration day.
--
-- "Expired" is deliberately NOT a stored status - it's derived by
-- comparing `ends_at` to `now()` wherever it's read. That avoids
-- needing a cron job to flip a status column and guarantees it's
-- always correct, at the cost of a `status` column that only ever
-- holds 'active' (the default, meaning "not cancelled early") or
-- 'cancelled' (an admin ended it before its natural end date).
create table if not exists company_subscriptions (
    id bigserial primary key,
    company_id uuid not null references companies(id) on delete cascade,
    status text not null check (status in ('active', 'cancelled')) default 'active',
    started_at timestamptz not null default now(),
    ends_at timestamptz not null,
    granted_by uuid references admin_users(id),
    created_at timestamptz not null default now()
);

create index if not exists idx_company_subscriptions_company_time
    on company_subscriptions (company_id, created_at desc);
