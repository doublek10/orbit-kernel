"""
Kernel API - general routes.

Auth bootstrapping (signup/login/refresh/logout) lives in auth_routes.py
since it's special (it's what *creates* an ExecutionContext). Everything
here operates on an ALREADY-issued Supabase access token:

- /identity/resolve: "who is this token, what can they do" - used by the
  Gateway's session check and internally by /execute below.
- /execute: the single generic entry point every other business
  capability (companies, dashboard, workflows, ...) goes through. The
  Gateway forwards every request here verbatim; the Kernel resolves
  identity fresh, then dispatches to the Workflow Engine. Nothing is
  cached or pre-decided by the Gateway.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from country_packages.registry import list_countries as list_countries_registry
from kernel.audit_logger.logger import AuditLogger
from kernel.health.health import HealthCheck
from kernel.kernel_api.security import require_gateway_secret
from kernel.request_router.router import RequestRouter
from kernel.workflow_engine.engine import WorkflowEngine
from shared.db import get_pool

router = APIRouter(prefix="/kernel/v1", dependencies=[Depends(require_gateway_secret)])
public_router = APIRouter(prefix="/kernel/v1")


class ResolveIdentityRequest(BaseModel):
    supabase_access_token: str
    company_id: str | None = None
    request_id: str | None = None


class ResolveIdentityResponse(BaseModel):
    identity: dict
    company: dict
    permissions: dict
    request_id: str | None
    metadata: dict


@router.post("/identity/resolve", response_model=ResolveIdentityResponse)
async def resolve_identity(body: ResolveIdentityRequest, request: Request):
    pool = get_pool()
    ctx = await RequestRouter(pool).build_context(
        supabase_access_token=body.supabase_access_token,
        company_id=body.company_id,
        request_id=body.request_id,
    )

    await AuditLogger(pool).record(
        actor_id=ctx.user_id,
        company_id=ctx.company_id,
        action="identity.resolved",
        metadata={"request_id": ctx.request_id},
    )

    return ctx.to_dict()


class ExecuteRequest(BaseModel):
    workflow: str
    payload: dict = {}
    supabase_access_token: str
    company_id: str | None = None
    request_id: str | None = None


@router.post("/execute")
async def execute(body: ExecuteRequest):
    """
    Every single non-auth request the Frontend makes ends up here, via
    the Gateway. This is what "the Kernel reviews every request" means in
    practice: identity is re-resolved from the token on every call - the
    Gateway holds no session state of its own to trust instead.
    """
    pool = get_pool()
    ctx = await RequestRouter(pool).build_context(
        supabase_access_token=body.supabase_access_token,
        company_id=body.company_id,
        request_id=body.request_id,
    )

    result = await WorkflowEngine(pool).run(ctx, body.workflow, body.payload)

    await AuditLogger(pool).record(
        actor_id=ctx.user_id,
        company_id=ctx.company_id,
        action=f"workflow.{body.workflow}",
        metadata={"request_id": ctx.request_id},
    )

    return result


@public_router.get("/health")
async def health():
    pool = get_pool()
    return await HealthCheck(pool).check()


class CountryOut(BaseModel):
    code: str
    name: str
    currency: str
    active: bool


@public_router.get("/countries", response_model=list[CountryOut])
async def list_countries():
    """Public and unauthenticated on purpose - the Frontend needs this
    to render the country picker on the registration screen, before any
    session exists. Per the spec: "The Frontend ... Retrieves available
    countries from the Kernel. Never hardcodes providers." Only
    `active` Country Packages should be selectable at signup; countries
    still being built out are returned too (so the Frontend can show
    them as "coming soon") but marked inactive."""
    return [
        CountryOut(code=c.code, name=c.name, currency=c.currency, active=c.active)
        for c in list_countries_registry()
    ]
