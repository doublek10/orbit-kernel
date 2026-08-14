"""
Admin API routes.

Everything the Admin Control Panel (admin-frontend, via admin-gateway)
talks to lives here, under /kernel/v1/admin. Mirrors the shape of the
tenant-facing kernel_api (auth_routes.py + routes.py) but is a fully
separate authentication and authorization system - see
kernel/admin/auth.py and kernel/kernel_api/admin_security.py.

Only two kinds of power live here, matching what was asked for:
  - visibility: per-company data flow/usage, Python process health,
    error codes, security alerts
  - one destructive action: deactivate/reactivate a company or a user

Nothing here executes tenant business workflows - that remains
exclusively the Workflow Engine's job via /kernel/v1/execute.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from kernel.admin.auth import AdminAuth, AdminAuthError, AdminIdentity
from kernel.admin.error_logger import ErrorLogger
from kernel.admin.security_alerts import SecurityAlerts
from kernel.admin.subscriptions import SubscriptionError, SubscriptionManager
from kernel.admin.usage_tracker import UsageTracker
from kernel.audit_logger.logger import AuditLogger
from kernel.health.health import HealthCheck
from kernel.kernel_api.admin_security import require_admin_identity
from kernel.kernel_api.security import require_gateway_secret
from fastapi import HTTPException, status
from shared.db import get_pool

# Login is reachable with only the gateway secret (there's no admin
# identity yet to check) - every other route additionally requires
# require_admin_identity, which itself depends on require_gateway_secret.
public_admin_router = APIRouter(
    prefix="/kernel/v1/admin", dependencies=[Depends(require_gateway_secret)]
)
admin_router = APIRouter(
    prefix="/kernel/v1/admin", dependencies=[Depends(require_admin_identity)]
)


# ── Auth ──────────────────────────────────────────────────────────────


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminOut(BaseModel):
    id: str
    username: str
    must_change_password: bool


class AdminLoginResponse(BaseModel):
    token: str
    expires_in: int
    admin: AdminOut


@public_admin_router.post("/auth/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest):
    pool = get_pool()
    auth = AdminAuth(pool)
    try:
        identity = await auth.authenticate(body.username, body.password)
    except AdminAuthError as exc:
        await SecurityAlerts(pool).record(
            severity="warning",
            category="failed_admin_login",
            message=f"Failed admin login attempt for username '{body.username}': {exc}",
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))

    token, ttl = auth.issue_token(identity)
    await AuditLogger(pool).record(
        actor_id=identity.admin_id, company_id=None, action="admin.auth.login"
    )
    return AdminLoginResponse(
        token=token,
        expires_in=ttl,
        admin=AdminOut(
            id=identity.admin_id,
            username=identity.username,
            must_change_password=identity.must_change_password,
        ),
    )


@admin_router.get("/auth/session", response_model=AdminOut)
async def admin_session(identity: AdminIdentity = Depends(require_admin_identity)):
    return AdminOut(
        id=identity.admin_id,
        username=identity.username,
        must_change_password=identity.must_change_password,
    )


class ChangePasswordRequest(BaseModel):
    new_password: str


@admin_router.post("/auth/change-password")
async def admin_change_password(
    body: ChangePasswordRequest, identity: AdminIdentity = Depends(require_admin_identity)
):
    pool = get_pool()
    try:
        await AdminAuth(pool).change_password(identity.admin_id, body.new_password)
    except AdminAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    await AuditLogger(pool).record(
        actor_id=identity.admin_id, company_id=None, action="admin.auth.change_password"
    )
    return {"ok": True}


# ── Overview: per-company usage + Python health in one call ────────────


@admin_router.get("/overview")
async def admin_overview(since_hours: int = Query(default=24, ge=1, le=24 * 30)):
    pool = get_pool()
    usage = await UsageTracker(pool).summary(since_hours=since_hours)
    health = await HealthCheck(pool).check()
    open_alerts = await SecurityAlerts(pool).list(resolved=False, limit=5)
    return {
        "companies": usage,
        "kernel_health": health,
        "open_security_alerts": open_alerts,
    }


# ── Companies ────────────────────────────────────────────────────────


@admin_router.get("/companies")
async def admin_list_companies(since_hours: int = Query(default=24, ge=1, le=24 * 30)):
    return {"companies": await UsageTracker(pool=get_pool()).summary(since_hours=since_hours)}


class CompanyStatusRequest(BaseModel):
    is_active: bool


@admin_router.post("/companies/{company_id}/status")
async def admin_set_company_status(
    company_id: str,
    body: CompanyStatusRequest,
    identity: AdminIdentity = Depends(require_admin_identity),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE companies SET is_active = $1 WHERE id = $2", body.is_active, company_id
        )
    if result == "UPDATE 0":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")

    action = "admin.company.activated" if body.is_active else "admin.company.deactivated"
    await AuditLogger(pool).record(
        actor_id=identity.admin_id, company_id=company_id, action=action
    )
    if not body.is_active:
        await SecurityAlerts(pool).record(
            severity="info",
            category="company_deactivated",
            message=f"Company {company_id} was deactivated by admin '{identity.username}'.",
            company_id=company_id,
        )
    return {"ok": True, "company_id": company_id, "is_active": body.is_active}


# ── Company subscriptions ───────────────────────────────────────────
# "Once it's activated" - grant() itself enforces that the company is
# active (SubscriptionError -> 400 otherwise). A subscription starts
# immediately and runs for exactly one calendar month; granting again
# later starts a fresh month from that later date (an explicit renewal,
# not something that stacks silently).


@admin_router.get("/companies/{company_id}/subscription")
async def admin_get_subscription(company_id: str):
    sub = await SubscriptionManager(get_pool()).current(company_id)
    return {"subscription": sub}


@admin_router.post("/companies/{company_id}/subscription")
async def admin_grant_subscription(
    company_id: str, identity: AdminIdentity = Depends(require_admin_identity)
):
    pool = get_pool()
    try:
        sub = await SubscriptionManager(pool).grant(company_id, identity.admin_id)
    except SubscriptionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    await AuditLogger(pool).record(
        actor_id=identity.admin_id,
        company_id=company_id,
        action="admin.company.subscription_granted",
        metadata={"ends_at": sub["ends_at"]},
    )
    return {"subscription": sub}


@admin_router.post("/companies/{company_id}/subscription/cancel")
async def admin_cancel_subscription(
    company_id: str, identity: AdminIdentity = Depends(require_admin_identity)
):
    pool = get_pool()
    await SubscriptionManager(pool).cancel(company_id)
    await AuditLogger(pool).record(
        actor_id=identity.admin_id,
        company_id=company_id,
        action="admin.company.subscription_cancelled",
    )
    return {"ok": True}


# ── Users ────────────────────────────────────────────────────────────


@admin_router.get("/users")
async def admin_list_users(search: str | None = Query(default=None)):
    pool = get_pool()
    async with pool.acquire() as conn:
        if search:
            rows = await conn.fetch(
                """
                SELECT u.id, u.email, u.full_name, u.is_active, u.created_at,
                       coalesce(
                           jsonb_agg(
                               jsonb_build_object(
                                   'company_id', c.id, 'company_name', c.name, 'role', m.role
                               )
                           ) FILTER (WHERE c.id IS NOT NULL), '[]'
                       ) AS companies
                FROM users u
                LEFT JOIN company_members m ON m.user_id = u.id
                LEFT JOIN companies c ON c.id = m.company_id
                WHERE u.email ILIKE $1 OR u.full_name ILIKE $1
                GROUP BY u.id
                ORDER BY u.created_at DESC
                """,
                f"%{search}%",
            )
        else:
            rows = await conn.fetch(
                """
                SELECT u.id, u.email, u.full_name, u.is_active, u.created_at,
                       coalesce(
                           jsonb_agg(
                               jsonb_build_object(
                                   'company_id', c.id, 'company_name', c.name, 'role', m.role
                               )
                           ) FILTER (WHERE c.id IS NOT NULL), '[]'
                       ) AS companies
                FROM users u
                LEFT JOIN company_members m ON m.user_id = u.id
                LEFT JOIN companies c ON c.id = m.company_id
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT 200
                """
            )
    return {
        "users": [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "full_name": r["full_name"],
                "is_active": r["is_active"],
                "created_at": r["created_at"].isoformat(),
                "companies": r["companies"],
            }
            for r in rows
        ]
    }


class UserStatusRequest(BaseModel):
    is_active: bool


@admin_router.post("/users/{user_id}/status")
async def admin_set_user_status(
    user_id: str,
    body: UserStatusRequest,
    identity: AdminIdentity = Depends(require_admin_identity),
):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET is_active = $1 WHERE id = $2", body.is_active, user_id
        )
    if result == "UPDATE 0":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    action = "admin.user.activated" if body.is_active else "admin.user.deactivated"
    await AuditLogger(pool).record(actor_id=identity.admin_id, company_id=None, action=action)
    if not body.is_active:
        await SecurityAlerts(pool).record(
            severity="info",
            category="user_deactivated",
            message=f"User {user_id} was deactivated by admin '{identity.username}'.",
        )
    return {"ok": True, "user_id": user_id, "is_active": body.is_active}


# ── Kernel / Python health ──────────────────────────────────────────


@admin_router.get("/health")
async def admin_health():
    return await HealthCheck(get_pool()).check()


# ── Errors ───────────────────────────────────────────────────────────


@admin_router.get("/errors")
async def admin_list_errors(
    code: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500)
):
    pool = get_pool()
    logger = ErrorLogger(pool)
    return {
        "errors": await logger.list(limit=limit, code=code),
        "codes": await logger.codes_summary(),
    }


@admin_router.get("/errors/{error_id}")
async def admin_get_error(error_id: int):
    error = await ErrorLogger(get_pool()).get(error_id)
    if error is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Error not found")
    return error


# ── Security alerts ─────────────────────────────────────────────────


@admin_router.get("/security-alerts")
async def admin_list_security_alerts(
    resolved: bool | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500)
):
    return {"alerts": await SecurityAlerts(get_pool()).list(resolved=resolved, limit=limit)}


@admin_router.post("/security-alerts/{alert_id}/resolve")
async def admin_resolve_security_alert(
    alert_id: int, identity: AdminIdentity = Depends(require_admin_identity)
):
    pool = get_pool()
    await SecurityAlerts(pool).resolve(alert_id)
    await AuditLogger(pool).record(
        actor_id=identity.admin_id,
        company_id=None,
        action="admin.security_alert.resolved",
        metadata={"alert_id": alert_id},
    )
    return {"ok": True}
