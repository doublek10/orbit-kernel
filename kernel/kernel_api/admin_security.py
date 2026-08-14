"""
Admin API guard.

Two independent checks stack on every admin route (except login itself):
1. `require_gateway_secret` - proves the call came from a trusted
   gateway (the Admin Gateway, using `admin_gateway_shared_secret`).
2. A valid admin session token in the `Authorization: Bearer` header -
   proves *which* operator is calling and that they're still active.

A leaked gateway secret alone is not enough to act as an admin, and a
leaked admin token alone is not enough either (it still has to arrive
via a trusted gateway). This mirrors exactly how the tenant-facing
Kernel API treats the Supabase access token vs. the Gateway secret.
"""

from fastapi import Depends, Header, HTTPException, status

from kernel.admin.auth import AdminAuth, AdminAuthError, AdminIdentity
from kernel.admin.security_alerts import SecurityAlerts
from kernel.kernel_api.security import require_gateway_secret
from shared.db import get_pool


async def require_admin_identity(
    authorization: str | None = Header(default=None),
    _: None = Depends(require_gateway_secret),
) -> AdminIdentity:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing admin session token")

    token = authorization.removeprefix("Bearer ").strip()
    auth = AdminAuth(get_pool())

    try:
        return auth.verify_token(token)
    except AdminAuthError as exc:
        try:
            await SecurityAlerts(get_pool()).record(
                severity="warning",
                category="invalid_admin_session",
                message=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
