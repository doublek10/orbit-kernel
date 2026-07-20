"""
The Kernel is never exposed to the internet - only the Gateway talks to
it, over the private network. As defense in depth, every request must
still present a shared secret proving it came from the Gateway.
"""

import hmac

from fastapi import Header, HTTPException, status

from shared.config import get_settings


async def require_gateway_secret(x_gateway_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_gateway_secret or not hmac.compare_digest(
        x_gateway_secret, settings.gateway_shared_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid gateway secret")
