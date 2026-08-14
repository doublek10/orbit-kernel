-- Attaches a fixed price to every company subscription.
--
-- Deliberately just a stored/displayed number - there is still no
-- payment processing anywhere in this system. This is a record of what
-- the subscription is worth, for the admin to see and for future
-- invoicing/billing work to read from, not a charge that actually
-- happens. If per-company custom pricing is ever needed, this is the
-- column to make ALTERable per row instead of relying on the default -
-- for now every company is uniformly $150.00/month.
alter table company_subscriptions
    add column if not exists amount_cents integer not null default 15000;
alter table company_subscriptions
    add column if not exists currency text not null default 'USD';

-- No separate backfill needed: `ADD COLUMN ... DEFAULT` in Postgres
-- already applies the default value to every existing row as part of
-- the ALTER TABLE itself.
