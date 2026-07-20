"""
Kernel Auth Routes

Every one of these is only reachable by the Gateway (require_gateway_secret
dependency) - never directly by the internet, and never by the Frontend.

Concrete flow for signup, matching the platform's design exactly:

    Frontend submits {email, password, company_name}
        -> Gateway (validates shape, forwards as-is, decides nothing)
        -> Kernel:
            1. Calls Supabase Admin API to create the identity
            2. Supabase returns a UUID
            3. Kernel uses that UUID to create the company + owner
               membership row in its own Postgres (VPN/private, not Supabase)
            4. Kernel signs the new user in to get a usable session
            5. Kernel returns success/failure + session to the Gateway
        -> Gateway relays the result to the Frontend, sets cookies
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from country_packages.registry import get_loaded_package, is_active
from kernel.audit_logger.logger import AuditLogger
from kernel.company_blueprint.version_manager import VersionManager
from kernel.company_resolver.onboarding import create_company_and_owner
from kernel.company_resolver.resolver import CompanyResolver
from kernel.kernel_api.security import require_gateway_secret
from kernel.permission_engine.engine import PermissionEngine
from shared.auth.supabase_admin import supabase_auth
from shared.config import get_settings
from shared.db import get_pool

router = APIRouter(prefix="/kernel/v1/auth", dependencies=[Depends(require_gateway_secret)])


class SessionOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class IdentityOut(BaseModel):
    user_id: str
    email: str


class CompanyOut(BaseModel):
    id: str
    name: str
    country: str
    role: str
    permissions: list[str]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    full_name: str | None = None
    country: str | None = None


class AuthResult(BaseModel):
    identity: IdentityOut
    company: CompanyOut
    session: SessionOut


@router.post("/signup", response_model=AuthResult)
async def signup(body: SignupRequest):
    pool = get_pool()
    settings = get_settings()

    country = (body.country or settings.default_country or "").upper()

    # Gateway already checked the shape; the Kernel is the one that
    # actually owns the Country Package registry, so it's the one that
    # verifies the chosen country is a real, currently-supported
    # package (spec: "Validate Package" during Registration Flow).
    # Raises ValueError -> the app-level handler turns this into a 400,
    # same as any other invalid-input case - never a silent fallback to
    # a different country than the one the Company Owner picked.
    if not is_active(country):
        raise ValueError(
            f"'{country}' is not a currently supported country. "
            "Choose one of the active countries returned by GET /kernel/v1/countries."
        )

    # Step 1 + 2: Kernel submits the authentication to Supabase, Supabase
    # hands back a UUID for the new identity.
    supabase_user = await supabase_auth.create_user(email=body.email, password=body.password)

    # Step 3: Kernel uses that UUID to create the company + owner
    # membership in its own self-hosted Postgres - never in Supabase.
    onboarded = await create_company_and_owner(
        pool,
        user_id=supabase_user.id,
        email=supabase_user.email,
        full_name=body.full_name,
        company_name=body.company_name,
        country=country,
    )

    # Step 3b: Plugin Manager loads the Country Package -> Load Country
    # Defaults -> Generate Initial Company Blueprint -> Store Blueprint.
    # This is what makes the chosen Country Package "activated" the
    # instant the company exists, rather than only the next time
    # someone happens to publish a Blueprint by hand.
    country_pkg = get_loaded_package(country)
    if country_pkg is not None and country_pkg.defaults is not None:
        await VersionManager(pool).publish(
            company_id=onboarded.company_id,
            published_by=supabase_user.id,
            payload=dict(country_pkg.defaults.DEFAULT_BLUEPRINT),
        )

    # Step 4: sign the new user in immediately so they leave with a
    # usable session instead of having to log in again right after.
    session = await supabase_auth.password_grant(email=body.email, password=body.password)

    await AuditLogger(pool).record(
        actor_id=supabase_user.id,
        company_id=onboarded.company_id,
        action="auth.signup",
        metadata={"email": supabase_user.email, "company_name": onboarded.company_name, "country": country},
    )

    # Step 5: success travels back to the Gateway, which relays it to the Frontend.
    return AuthResult(
        identity=IdentityOut(user_id=supabase_user.id, email=supabase_user.email),
        company=CompanyOut(
            id=onboarded.company_id,
            name=onboarded.company_name,
            country=onboarded.country,
            role=onboarded.role,
            permissions=["*"],  # owner, per create_company_and_owner
        ),
        session=SessionOut(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
        ),
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    company_id: str | None = None


@router.post("/login", response_model=AuthResult)
async def login(body: LoginRequest):
    pool = get_pool()

    session = await supabase_auth.password_grant(email=body.email, password=body.password)

    company = await CompanyResolver(pool).resolve(session.user.id, body.company_id)
    permissions = await PermissionEngine(pool).resolve(session.user.id, company.id)

    await AuditLogger(pool).record(
        actor_id=session.user.id,
        company_id=company.id,
        action="auth.login",
        metadata={"email": session.user.email},
    )

    return AuthResult(
        identity=IdentityOut(user_id=session.user.id, email=session.user.email),
        company=CompanyOut(
            id=company.id,
            name=company.name,
            country=company.country,
            role=permissions.role,
            permissions=permissions.grants,
        ),
        session=SessionOut(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
        ),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=SessionOut)
async def refresh(body: RefreshRequest):
    session = await supabase_auth.refresh(refresh_token=body.refresh_token)
    return SessionOut(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
    )


class LogoutRequest(BaseModel):
    access_token: str


@router.post("/logout")
async def logout(body: LogoutRequest):
    await supabase_auth.revoke(access_token=body.access_token)
    return {"ok": True}
