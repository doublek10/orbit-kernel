-- Orbit Kernel - marketplace installs
--
-- The catalog itself is static/in-code for now (first-party modules only
-- - there's no third-party developer submission pipeline yet). This
-- table just tracks which of those modules each company has turned on.

create table if not exists company_installed_apps (
    company_id uuid not null references companies(id) on delete cascade,
    app_key text not null,
    installed_at timestamptz not null default now(),
    primary key (company_id, app_key)
);
