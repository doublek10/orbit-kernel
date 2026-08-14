from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Self-hosted Postgres, reachable only over the private VPN ---
    database_url: str = "postgresql://orbit:orbit@localhost:5432/orbit"
    database_pool_min: int = 1
    database_pool_max: int = 10

    # --- Supabase: used ONLY for authentication, exclusively by the Kernel ---
    supabase_url: str = "https://ddmtepobrclgvcikcnjw.supabase.co"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRkbXRlcG9icmNsZ3ZjaWtjbmp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxNDc2OTIsImV4cCI6MjA5NDcyMzY5Mn0.YFIfJnqxi1WcxuXPQp783PAyX5koM5R4HDYJ-ZCZGro"
    supabase_service_role_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRkbXRlcG9icmNsZ3ZjaWtjbmp3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTE0NzY5MiwiZXhwIjoyMDk0NzIzNjkyfQ.rJokR-v_bkq9Nyy-1NZ2PFSIdYmV88v_jtutSbSQ2tY"
    # Access tokens are verified either against Supabase's published JWKS
    # (asymmetric ES256/RS256 - "JWT Signing Keys" projects) or against
    # this shared secret (legacy HS256 projects). Which path is used is
    # decided per-token from its own header in shared/auth/supabase_jwt.py,
    # since a project can only be signing with one of the two at a time.
    # This project currently signs with the legacy HS256 secret, so this
    # value MUST be set (it was previously present in .env but silently
    # dropped because this field didn't exist here - extra="ignore" above
    # swallows unknown env vars instead of erroring).
    supabase_jwt_secret: str = ""
    # `supabase_jwt_audience` is checked as part of verification for
    # both paths above.
    supabase_jwt_audience: str = "authenticated"

    @field_validator("supabase_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        # Normalized ONCE, here, so every consumer (token signing in
        # supabase_admin.py, JWKS lookup in supabase_jwt.py, and anything
        # added later) gets a consistent value - a stray trailing slash
        # in the env var previously produced a double slash in the JWKS
        # URL specifically, silently resolving to a different/stale
        # keyset than the one actually used to sign tokens.
        return v.rstrip("/")

    # --- Public base URL the Gateway is reachable at - used only to
    # construct the "Company Endpoint" URL shown in the API Generator.
    # No route actually receives events at that URL yet - generating the
    # identity (slug + signing secret) is real, but live ingestion is a
    # separate, not-yet-built piece (same honesty convention as
    # /api/webhooks, which is an explicit 501 today).
    gateway_public_base_url: str = "https://orbit-gateway.vercel.app"

    # --- Service-to-service trust between Gateway and Kernel ---
    gateway_shared_secret: str = "Y9KqPzvJ2N8x5LwE7fHnQbRmT6sVaU4yZcX1pFd8GjNk3mCrPwLq0eHs9iBuMvAx"

    # --- Service-to-service trust between the SEPARATE Admin Gateway and
    # this same Kernel. Kept distinct from gateway_shared_secret so the
    # admin control plane's credential can be rotated independently of
    # the tenant-facing Gateway's, and so a leak of one never implies the
    # other. Must exactly match the Admin Gateway's own env var.
    admin_gateway_shared_secret: str = "changeme-admin-gateway-shared-secret"

    # --- Admin Control Panel session signing. Entirely separate from
    # Supabase - the admin_users table and this secret are the Kernel's
    # own, self-contained authentication system for platform operators.
    # Generate a long random value in production, e.g. `openssl rand -hex 32`.
    admin_jwt_secret: str = "changeme-generate-a-long-random-admin-jwt-secret"
    admin_session_ttl_seconds: int = 60 * 60 * 8  # 8 hours

    # --- Security Engine: symmetric key for encrypting credentials at
    # rest (Blueprint provider connections, webhook signing secrets).
    # Must be a urlsafe-base64-encoded 32-byte key - generate with
    # `Fernet.generate_key()`. Rotate by re-encrypting with a new key;
    # the Security Engine never stores plaintext, even transiently
    # outside of a single request.
    blueprint_encryption_key: str = "changeme-generate-with-fernet-generate-key-32-bytes-b64="

    # --- Server ---
    kernel_host: str = "0.0.0.0"
    kernel_port: int = 60013
    environment: str = "development"

    # Default country for a newly created company when none is supplied.
    default_country: str = "KE"


@lru_cache
def get_settings() -> Settings:
    return Settings()
