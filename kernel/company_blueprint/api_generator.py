"""
API Generator

Creates the Company Endpoint identity: a unique URL slug and an HMAC
signing secret, so a company's own systems can eventually push events to
Orbit and have them verified as genuinely coming from that company.
Reuses the existing api_keys table (kernel/workflow_engine/engine.py's
developer.* handlers) for bearer-token authentication - this module only
owns what's specific to the endpoint: the slug, the signing secret, and
its rate limit.

Signing uses HMAC-SHA256 over the raw request body, the same mechanism
Stripe/GitHub webhooks use. Verification is constant-time
(hmac.compare_digest) to avoid timing attacks on the comparison itself.
"""

import hmac
import secrets
from dataclasses import dataclass
from hashlib import sha256

import asyncpg

from kernel.company_blueprint.encryption import decrypt_secret, encrypt_secret


def sign_payload(secret: str, raw_body: str) -> str:
    return hmac.new(secret.encode(), raw_body.encode(), sha256).hexdigest()


def verify_signature(secret: str, raw_body: str, signature: str) -> bool:
    expected = sign_payload(secret, raw_body)
    return hmac.compare_digest(expected, signature)


@dataclass(frozen=True)
class CompanyEndpoint:
    endpoint_slug: str
    rate_limit_per_minute: int
    created_at: str
    rotated_at: str | None

    def to_dict(self, base_url: str) -> dict:
        return {
            "endpoint_slug": self.endpoint_slug,
            "endpoint_url": f"{base_url}/api/ingest/{self.endpoint_slug}",
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "created_at": self.created_at,
            "rotated_at": self.rotated_at,
        }


class ApiGeneratorStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get(self, company_id: str) -> CompanyEndpoint | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM company_endpoints WHERE company_id = $1", company_id
            )
        return self._row(row) if row else None

    async def get_or_create(self, company_id: str) -> tuple[CompanyEndpoint, str | None]:
        """Returns (endpoint, new_secret). new_secret is only non-None the
        moment the endpoint is first created - same one-time-reveal
        contract as api_keys."""
        existing = await self.get(company_id)
        if existing is not None:
            return existing, None

        slug = f"co-{secrets.token_urlsafe(12)}".lower().replace("_", "-")
        raw_secret = secrets.token_urlsafe(32)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO company_endpoints (company_id, endpoint_slug, webhook_secret_encrypted)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                company_id,
                slug,
                encrypt_secret(raw_secret),
            )
        return self._row(row), raw_secret

    async def rotate(self, company_id: str) -> tuple[CompanyEndpoint, str]:
        raw_secret = secrets.token_urlsafe(32)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE company_endpoints
                SET webhook_secret_encrypted = $1, rotated_at = now()
                WHERE company_id = $2
                RETURNING *
                """,
                encrypt_secret(raw_secret),
                company_id,
            )
        if row is None:
            raise ValueError("No endpoint exists yet - generate one first")
        return self._row(row), raw_secret

    async def get_decrypted_secret(self, company_id: str) -> str | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT webhook_secret_encrypted FROM company_endpoints WHERE company_id = $1",
                company_id,
            )
        return decrypt_secret(row["webhook_secret_encrypted"]) if row else None

    @staticmethod
    def _row(row) -> CompanyEndpoint:
        return CompanyEndpoint(
            endpoint_slug=row["endpoint_slug"],
            rate_limit_per_minute=row["rate_limit_per_minute"],
            created_at=row["created_at"].isoformat(),
            rotated_at=row["rotated_at"].isoformat() if row["rotated_at"] else None,
        )
