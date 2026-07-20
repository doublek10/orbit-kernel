"""
Security Engine (overview)

The Security page is deliberately a VIEW, not new machinery - every
credential and permission it displays already has a real owner
elsewhere (developer.* for API keys, ApiGeneratorStore for the webhook
secret, company_members for ownership). This module's only job is to
assemble those into one honest picture, plus one genuine check of its
own: verify_credential_integrity actually attempts to decrypt the
stored webhook secret and reports whether it succeeds - a real
detector for the case where the encryption key has rotated out from
under stored data, not a cosmetic status light.

"Certificate Status" in the spec maps onto that credential-integrity
check: Orbit doesn't issue X.509 certificates, so this reports on the
signing credential's usability instead of fabricating PKI details that
don't exist.
"""

import asyncpg

from kernel.company_blueprint.api_generator import ApiGeneratorStore
from kernel.company_blueprint.encryption import DecryptionError, decrypt_secret
from kernel.audit_logger.logger import AuditLogger


async def verify_credential_integrity(pool: asyncpg.Pool, company_id: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT webhook_secret_encrypted FROM company_endpoints WHERE company_id = $1",
            company_id,
        )
    if row is None:
        return {"status": "not_configured", "detail": "No Company Endpoint generated yet."}

    try:
        decrypt_secret(row["webhook_secret_encrypted"])
    except DecryptionError:
        return {
            "status": "invalid",
            "detail": "The stored webhook secret can't be decrypted with the current encryption "
            "key - rotate it.",
        }
    return {"status": "valid", "detail": "Webhook signing credential is intact and usable."}


async def get_security_overview(
    pool: asyncpg.Pool, company_id: str, api_generator: ApiGeneratorStore
) -> dict:
    async with pool.acquire() as conn:
        key_rows = await conn.fetch(
            """
            SELECT id, name, key_prefix, created_at, last_used_at, revoked
            FROM api_keys WHERE company_id = $1 ORDER BY created_at DESC
            """,
            company_id,
        )
        member_rows = await conn.fetch(
            """
            SELECT u.email, cm.role, cm.permissions
            FROM company_members cm
            JOIN users u ON u.id = cm.user_id
            WHERE cm.company_id = $1
            ORDER BY (cm.role = 'owner') DESC, u.email
            """,
            company_id,
        )

    api_keys = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "key_prefix": r["key_prefix"],
            "created_at": r["created_at"].isoformat(),
            "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
            "revoked": r["revoked"],
        }
        for r in key_rows
    ]

    endpoint = await api_generator.get(company_id)
    credential_status = await verify_credential_integrity(pool, company_id)

    members = [
        {"email": r["email"], "role": r["role"], "permissions": list(r["permissions"] or [])}
        for r in member_rows
    ]

    activity = await AuditLogger(pool).list_events(company_id, limit=25)

    return {
        "api_keys": {
            "active": [k for k in api_keys if not k["revoked"]],
            "revoked": [k for k in api_keys if k["revoked"]],
        },
        "webhook_secret": {
            "configured": endpoint is not None,
            "rotated_at": endpoint.rotated_at if endpoint else None,
            "created_at": endpoint.created_at if endpoint else None,
        },
        "certificate_status": credential_status,
        "ownership": {"members": members},
        "recent_activity": activity,
    }
