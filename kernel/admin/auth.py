"""
Admin Auth

A deliberately separate authentication path for the internal Admin
Control Panel. Tenant users authenticate via Supabase (see
shared/auth/supabase_admin.py, supabase_jwt.py) - operators of the
platform itself never touch Supabase at all. Instead they authenticate
against an `admin_users` table in this same self-hosted Postgres,
verified with Postgres' own pgcrypto `crypt()` (bcrypt), so the Kernel
never needs a Python password-hashing dependency and a plaintext
password never leaves a single parameterised query.

Admin sessions are short-lived JWTs signed with `admin_jwt_secret`
(distinct from the Supabase JWT secret). The Kernel issues and verifies
these itself; the Admin Gateway only stores/forwards the token in an
httpOnly cookie, exactly as the tenant Gateway does for Supabase tokens
- it never decodes or trusts it locally.
"""

import time
from dataclasses import dataclass

import asyncpg
import jwt

from shared.config import get_settings


class AdminAuthError(Exception):
    """Raised for any admin-auth failure. Callers translate this to a
    401 - the message is safe to show to an operator (it never leaks
    whether a username exists vs. a password being wrong, on purpose)."""


@dataclass(frozen=True)
class AdminIdentity:
    admin_id: str
    username: str
    must_change_password: bool


class AdminAuth:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def authenticate(self, username: str, password: str) -> AdminIdentity:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, is_active, must_change_password,
                       (password_hash = crypt($2, password_hash)) AS password_ok
                FROM admin_users
                WHERE username = $1
                """,
                username,
                password,
            )

        # Same generic message whether the username doesn't exist or the
        # password is wrong - don't help an attacker enumerate usernames.
        if row is None or not row["password_ok"]:
            raise AdminAuthError("Invalid username or password")
        if not row["is_active"]:
            raise AdminAuthError("This admin account has been deactivated")

        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE admin_users SET last_login_at = now() WHERE id = $1", row["id"]
            )

        return AdminIdentity(
            admin_id=str(row["id"]),
            username=row["username"],
            must_change_password=row["must_change_password"],
        )

    async def change_password(self, admin_id: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise AdminAuthError("New password must be at least 8 characters")
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE admin_users
                SET password_hash = crypt($2, gen_salt('bf')), must_change_password = false
                WHERE id = $1
                """,
                admin_id,
                new_password,
            )
        if result == "UPDATE 0":
            raise AdminAuthError("Admin account not found")

    def issue_token(self, identity: AdminIdentity) -> tuple[str, int]:
        settings = get_settings()
        ttl = settings.admin_session_ttl_seconds
        now = int(time.time())
        payload = {
            "sub": identity.admin_id,
            "username": identity.username,
            "iat": now,
            "exp": now + ttl,
            "scope": "admin",
        }
        token = jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")
        return token, ttl

    def verify_token(self, token: str) -> AdminIdentity:
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.admin_jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise AdminAuthError(f"Invalid or expired admin session: {exc}")
        if payload.get("scope") != "admin":
            raise AdminAuthError("Invalid admin session")
        return AdminIdentity(
            admin_id=payload["sub"],
            username=payload["username"],
            must_change_password=False,
        )
