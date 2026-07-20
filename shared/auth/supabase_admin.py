"""
Supabase Auth client.

This is the ONLY file in the entire platform that makes a network call to
Supabase. The Frontend never does; the Gateway never does. Supabase's job
is strictly: create identities, verify passwords, issue/refresh/revoke
tokens. It never sees company data, permissions, or anything business
related - that all lives in the Kernel's own Postgres.
"""

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from shared.config import get_settings


@dataclass(frozen=True)
class SupabaseUser:
    id: str
    email: str


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user: SupabaseUser


class SupabaseAuthClient:
    def __init__(self):
        settings = get_settings()
        self._base_url = settings.supabase_url.rstrip("/")
        self._anon_key = settings.supabase_anon_key
        self._service_role_key = settings.supabase_service_role_key

    async def create_user(self, *, email: str, password: str) -> SupabaseUser:
        """
        Admin-creates a pre-confirmed user. Uses the service-role key,
        which only the Kernel ever holds. This is what makes signup a
        single atomic step instead of a "check your email" flow - trade
        that for real email verification later if the product needs it.
        """
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/auth/v1/admin/users",
                headers=self._admin_headers(),
                json={"email": email, "password": password, "email_confirm": True},
            )
        if res.status_code >= 400:
            self._raise(res, default_status=status.HTTP_400_BAD_REQUEST)
        body = res.json()
        return SupabaseUser(id=body["id"], email=body["email"])

    async def password_grant(self, *, email: str, password: str) -> SupabaseSession:
        """Signs in with email/password - what the Kernel does on login,
        and again right after signup so the caller leaves with a usable
        session in one round trip."""
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/auth/v1/token",
                params={"grant_type": "password"},
                headers=self._anon_headers(),
                json={"email": email, "password": password},
            )
        if res.status_code >= 400:
            self._raise(res, default_status=status.HTTP_401_UNAUTHORIZED)
        return self._parse_session(res.json())

    async def refresh(self, *, refresh_token: str) -> SupabaseSession:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/auth/v1/token",
                params={"grant_type": "refresh_token"},
                headers=self._anon_headers(),
                json={"refresh_token": refresh_token},
            )
        if res.status_code >= 400:
            self._raise(res, default_status=status.HTTP_401_UNAUTHORIZED)
        return self._parse_session(res.json())

    async def revoke(self, *, access_token: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base_url}/auth/v1/logout",
                headers={**self._anon_headers(), "Authorization": f"Bearer {access_token}"},
            )
        # Best-effort: even if Supabase is briefly unreachable, the Kernel
        # still treats logout as successful locally (the token will
        # simply expire naturally).

    def _admin_headers(self) -> dict:
        return {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Content-Type": "application/json",
        }

    def _anon_headers(self) -> dict:
        return {"apikey": self._anon_key, "Content-Type": "application/json"}

    def _parse_session(self, body: dict) -> SupabaseSession:
        user = body["user"]
        return SupabaseSession(
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            expires_in=body["expires_in"],
            user=SupabaseUser(id=user["id"], email=user["email"]),
        )

    def _raise(self, res: httpx.Response, *, default_status: int) -> None:
        try:
            detail = res.json().get("msg") or res.json().get("error_description") or res.text
        except Exception:
            detail = res.text
        raise HTTPException(res.status_code or default_status, f"Supabase error: {detail}")


supabase_auth = SupabaseAuthClient()
