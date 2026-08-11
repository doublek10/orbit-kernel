"""
Verifies Supabase-issued access tokens.

Supabase's ONLY role in this platform is authentication: it proves that a
request comes from a real, logged-in user and hands us their stable user id
(the JWT `sub` claim) and email. Everything else about that user - which
company they belong to, what role they hold, what they're allowed to do -
is business data that lives in the Kernel's own Postgres and is resolved by
the Company Resolver / Permission Engine, never by Supabase.

Verification method depends on how the Supabase project is configured to
sign tokens, and a project only ever signs with one of the two at a time:

  - Legacy projects sign with a shared HS256 secret (SUPABASE_JWT_SECRET).
    There is no public key for these - they can't be published via JWKS,
    since HS256 is symmetric - so they must be verified directly against
    the secret.
  - Projects that have switched to Supabase's "JWT Signing Keys" feature
    sign with asymmetric keys (ES256/RS256), verified against Supabase's
    published JWKS. PyJWKClient fetches and caches those public keys and
    handles key rotation automatically, so there is no secret to keep in
    sync for this path.

Which path applies is read from the token's own header (`alg`) rather than
assumed, so this keeps working unchanged if the project is ever migrated
from one signing mode to the other.
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from shared.config import get_settings

_ASYMMETRIC_ALGS = ("ES256", "RS256")
_SYMMETRIC_ALGS = ("HS256",)


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: str
    email: str | None
    raw_claims: dict


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    settings = get_settings()
    # Supabase's standard JWKS endpoint - publishes the public keys used
    # to sign access tokens when the project uses asymmetric signing.
    # Cached per-process; PyJWKClient itself also caches individual keys
    # and re-fetches on an unrecognized kid, so key rotation on Supabase's
    # side doesn't require a Kernel restart.
    return PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def verify_supabase_token(token: str) -> VerifiedIdentity:
    settings = get_settings()
    try:
        alg = jwt.get_unverified_header(token).get("alg")

        if alg in _SYMMETRIC_ALGS:
            # Legacy HS256 project: verify directly against the shared
            # secret. There is no kid/JWKS lookup involved - a project
            # signing this way never publishes a matching JWKS entry, so
            # routing these tokens through PyJWKClient (the old bug here)
            # always fails with "unable to verify signing key" regardless
            # of how valid the token actually is.
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    "Invalid token: SUPABASE_JWT_SECRET is not configured, but this "
                    "project signs tokens with HS256",
                )
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=list(_SYMMETRIC_ALGS),
                audience=settings.supabase_jwt_audience,
                options={"require": ["exp", "sub"]},
            )
        else:
            signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(_ASYMMETRIC_ALGS),
                audience=settings.supabase_jwt_audience,
                options={"require": ["exp", "sub"]},
            )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.PyJWKClientError as exc:
        # Raised by get_signing_key_from_jwt() itself, before jwt.decode()
        # ever runs - e.g. the token's `kid` doesn't match any key in
        # Supabase's published JWKS (already retried once internally by
        # PyJWKClient against a fresh fetch before raising this). This is
        # NOT a subclass of InvalidTokenError, so it needs its own clause -
        # without it, this exception was escaping uncaught and crashing
        # the whole request as an unhandled 500.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: unable to verify signing key ({exc})")
    except jwt.PyJWTError as exc:
        # Catch-all for anything else PyJWT can raise (InvalidTokenError
        # and its subclasses, plus any other library-level failure) so a
        # bad/malformed token can never crash the request as an unhandled
        # 500 - it always becomes a clean 401 the Gateway can relay as JSON.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}")

    return VerifiedIdentity(
        user_id=claims["sub"],
        email=claims.get("email"),
        raw_claims=claims,
    )
