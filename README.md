# Orbit Kernel - The Brain

### Engineering README

---

# Purpose

The Orbit Kernel is the execution engine of the Orbit Platform. It is
responsible for orchestrating every business operation performed within
the platform, including authentication. It owns all business rules, all
workflows, and every financial decision.

The Kernel is never exposed directly to the Internet. Only the Gateway
communicates with it, over a private network, and it is the ONLY
component in the entire platform that ever calls Supabase.

---

# System communication, end to end

```
Frontend  →  Gateway  →  Orbit Kernel  →  Everything
(display)    (security     (the brain)
              guard)              │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                    SUPABASE            POSTGRES
              (identity only: UUID,   (companies, users,
               password checks,       permissions, audit -
               token issuance)        self-hosted, VPN-only)
```

The Gateway forwards every single request here - auth or otherwise -
and trusts nothing from a previous request. Identity and permissions are
re-resolved fresh, every call.

---

# Worked example: sign up

`POST /kernel/v1/auth/signup` (in `kernel/kernel_api/auth_routes.py`),
given `{ email, password, company_name, full_name?, country? }`:

```
1. supabase_auth.create_user(email, password)
   → shared/auth/supabase_admin.py, using the service-role key
   → Supabase Admin API creates a pre-confirmed identity
   → returns a UUID + email

2. create_company_and_owner(pool, user_id=<UUID>, ...)
   → kernel/company_resolver/onboarding.py
   → ONE Postgres transaction:
       INSERT INTO users (id, email, full_name)
       INSERT INTO companies (name, country)
       INSERT INTO company_members (user_id, company_id, role='owner', permissions=["*"])
   → if any statement fails, the whole transaction rolls back - a
     Supabase identity can never end up without a company, and a
     company can never end up without an owner

3. supabase_auth.password_grant(email, password)
   → signs the new user in immediately, returns access/refresh tokens

4. AuditLogger.record(actor_id=UUID, action="auth.signup", ...)

5. Returns { identity, company, session } to the Gateway, which relays
   it (after normalizing the shape and setting cookies) to the Frontend.
```

Login (`/auth/login`) skips steps 1-2 and instead resolves the existing
company/permissions for that UUID via `CompanyResolver` +
`PermissionEngine`. Refresh and logout call Supabase's token-refresh and
logout endpoints respectively - see `auth_routes.py`.

---

# Every other request

`POST /kernel/v1/execute` (`kernel/kernel_api/routes.py`) is what every
non-auth Gateway call hits:

```
{ workflow, payload, supabase_access_token, company_id? }
    → RequestRouter.build_context()
         - verify_supabase_token(): local JWT signature check,
           no network call to Supabase needed for this part
         - CompanyResolver.resolve()
         - PermissionEngine.resolve()
    → WorkflowEngine.run(ctx, workflow, payload)
    → AuditLogger.record()
```

Today `WorkflowEngine.run()` raises `NotImplementedError` for every
workflow name - that's an honest, deliberate stub. Add a real branch per
capability as it's built.

---

# Repository Structure

```text
orbit-kernel/
│
├── README.md
├── main.py                       # mounts auth_routes + routes (identity/execute/health)
├── requirements.txt
├── .env.example
│
├── kernel/
│   ├── context.py                 # ExecutionContext shared by every module
│   ├── request_router/            # builds ExecutionContext from a token
│   ├── company_resolver/
│   │   ├── resolver.py             # resolves an EXISTING company for a user
│   │   └── onboarding.py            # creates company+owner from a fresh Supabase UUID
│   ├── permission_engine/          # resolves role + grants from Postgres
│   ├── kernel_api/
│   │   ├── auth_routes.py           # signup / login / refresh / logout - Supabase lives here
│   │   ├── routes.py                 # identity/resolve + execute + health
│   │   └── security.py                # X-Gateway-Secret guard
│   ├── audit_logger/               # every action is recorded
│   ├── workflow_engine/             # dispatches /execute - stub per capability
│   ├── rule_engine/ provider_manager/ event_bus/ plugin_manager/
│   ├── scheduler/ service_registry/ feature_flags/ metrics/ health/
│
├── providers/ financial_graph/ replay/ ai/ marketplace/
├── country_packages/kenya/ enterprise/
│
├── shared/
│   ├── config.py                   # env-driven settings incl. Supabase keys
│   ├── db.py                        # asyncpg pool - self-hosted Postgres, VPN only
│   └── auth/
│       ├── supabase_jwt.py           # verifies an EXISTING token locally (no network call)
│       └── supabase_admin.py          # THE ONLY file that calls Supabase's API
│
├── migrations/001_init.sql          # users, companies, company_members, audit_log
└── tests/
```

---

# Responsibilities

The Kernel is responsible for: authenticating users (via Supabase),
executing workflows, running business rules, managing permissions,
building financial graphs, executing Replay simulations, managing
providers, scheduling background work, running AI orchestration,
publishing events, recording audits, loading plugins and country
packages, coordinating enterprise features.

The Kernel is **not** responsible for: rendering UI, HTTP routing exposed
to the internet, browser sessions, cookies, HTML, React, or Next.js.
Those belong to the Gateway and Frontend.

---

# Local Setup

1. Have a Postgres instance reachable (locally, `localhost`; in
   production, private/VPN-only, never public).
2. Create a Supabase project. From Project Settings → API, note the
   Project URL, `anon` key, `service_role` key, and JWT Secret.
3. `cp .env.example .env` and fill in `DATABASE_URL`, `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
   `SUPABASE_JWT_SECRET`, and a strong `GATEWAY_SHARED_SECRET` (must
   match the Gateway's `.env` exactly).
4. `psql "$DATABASE_URL" -f migrations/001_init.sql`
5. `python -m venv .venv && source .venv/bin/activate`
6. `pip install -r requirements.txt`
7. `uvicorn main:app --reload --port 8000`
8. `curl http://localhost:8000/kernel/v1/health`
9. Test signup end to end:
   ```
   curl -X POST http://localhost:8000/kernel/v1/auth/signup \
     -H "Content-Type: application/json" \
     -H "X-Gateway-Secret: <your GATEWAY_SHARED_SECRET>" \
     -d '{"email":"you@example.com","password":"correcthorsebattery","company_name":"Test Co"}'
   ```
   This should create a real Supabase user AND real rows in your
   Postgres `users`/`companies`/`company_members` tables in one shot.

---

# Development Rules

1. The Kernel owns all business logic, including authentication.
2. Every request enters through the Request Router (or auth_routes for bootstrapping).
3. Every workflow executes through the Workflow Engine.
4. Providers are accessed only through the Provider Manager.
5. AI never performs actions directly.
6. Business rules belong only in the Rule Engine.
7. Every completed workflow publishes events.
8. Every action is audited.
9. The Kernel must remain framework-agnostic.
10. The Kernel must never depend on the Gateway or any frontend application.
11. The Kernel is the only component that ever calls Supabase.

---

# Long-Term Vision

The Orbit Kernel is designed as a reusable financial orchestration engine.
Its purpose is to remain stable while applications, providers, countries
and technologies evolve around it. Every future Orbit product should
execute through the Kernel without requiring changes to the Kernel's core
architecture.
