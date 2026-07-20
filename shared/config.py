"""
Central configuration for the Orbit Kernel.

The Kernel is the only component in the platform that talks to Supabase.
It holds the service-role key (full admin rights over Supabase Auth) and
the anon key (for password-grant token exchange) - neither of these ever
touches the Gateway or the Frontend.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Self-hosted Postgres, reachable only over the private VPN ---
    database_url: str = "postgresql://orbit:orbit@localhost:5432/orbit"
    database_pool_min: int = 1
    database_pool_max: int = 10

    # --- Supabase: used ONLY for authentication, exclusively by the Kernel ---
    supabase_url: str = "https://your-project.supabase.co"
    supabase_anon_key: str = "changeme-anon-key"
    supabase_service_role_key: str = "changeme-service-role-key"
    # Project Settings -> API -> JWT Secret. Lets the Kernel verify a
    # previously-issued Supabase access token locally (no network call)
    # on every subsequent authenticated request.
    supabase_jwt_secret: str = "changeme-supabase-jwt-secret"
    supabase_jwt_audience: str = "authenticated"

    # --- Public base URL the Gateway is reachable at - used only to
    # construct the "Company Endpoint" URL shown in the API Generator.
    # No route actually receives events at that URL yet - generating the
    # identity (slug + signing secret) is real, but live ingestion is a
    # separate, not-yet-built piece (same honesty convention as
    # /api/webhooks, which is an explicit 501 today).
    gateway_public_base_url: str = "https://api.orbit.dev"

    # --- Service-to-service trust between Gateway and Kernel ---
    gateway_shared_secret: str = "changeme-gateway-shared-secret"

    # --- Security Engine: symmetric key for encrypting credentials at
    # rest (Blueprint provider connections, webhook signing secrets).
    # Must be a urlsafe-base64-encoded 32-byte key - generate with
    # `Fernet.generate_key()`. Rotate by re-encrypting with a new key;
    # the Security Engine never stores plaintext, even transiently
    # outside of a single request.
    blueprint_encryption_key: str = "changeme-generate-with-fernet-generate-key-32-bytes-b64="

    # --- Server ---
    kernel_host: str = "0.0.0.0"
    kernel_port: int = 8000
    environment: str = "development"

    # Default country for a newly created company when none is supplied.
    default_country: str = "KE"


@lru_cache
def get_settings() -> Settings:
    return Settings()
