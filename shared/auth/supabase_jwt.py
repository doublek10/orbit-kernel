"""
Verifies Supabase-issued access tokens.

Supabase's ONLY role in this platform is authentication: it proves that a
request comes from a real, logged-in user and hands us their stable user id
(the JWT `sub` claim) and email. Everything else about that user - which
company they belong to, what role they hold, what they're allowed to do -
is business data that lives in the Kernel's own Postgres and is resolved by
the Company Resolver / Permission Engine, never by Supabase.
"""

from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status

from shared.config import get_settings


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: str
    email: str | None
    raw_claims: dict


def verify_supabase_token(token: str) -> VerifiedIdentity:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}")

    return VerifiedIdentity(
        user_id=claims["sub"],
        email=claims.get("email"),
        raw_claims=claims,
    )
