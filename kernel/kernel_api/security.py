"""
The Kernel is never exposed to the internet - only the Gateway (and,
separately, the Admin Gateway) talk to it, over the private network. As
defense in depth, every request must still present a shared secret
proving it came from one of those two trusted callers.
"""

import hmac

from fastapi import Header, HTTPException, status

from shared.config import get_settings


async def require_gateway_secret(x_gateway_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if x_gateway_secret and hmac.compare_digest(x_gateway_secret, settings.gateway_shared_secret):
        return
    if x_gateway_secret and hmac.compare_digest(
        x_gateway_secret, settings.admin_gateway_shared_secret
    ):
        return

    await _log_secret_mismatch()
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid gateway secret")


async def _log_secret_mismatch() -> None:
    # Best-effort only - this check runs before we can be sure the DB
    # pool is even up (e.g. very early in boot), and a logging failure
    # here must never turn into a confusing 500 that hides the real
    # 401.
    try:
        from kernel.admin.security_alerts import SecurityAlerts
        from shared.db import get_pool

        await SecurityAlerts(get_pool()).record(
            severity="critical",
            category="gateway_secret_mismatch",
            message="A request presented a missing or invalid X-Gateway-Secret header.",
        )
    except Exception:
        pass
