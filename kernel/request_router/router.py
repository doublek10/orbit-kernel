"""
Request Router

The front door of the Kernel. Every request - regardless of which
workflow it will eventually reach - passes through here first. It builds
the ExecutionContext and dispatches to the right workflow. It does NOT
execute business rules itself; it only assembles context and hands off.
"""

import asyncpg

from kernel.company_resolver.resolver import CompanyResolver
from kernel.context import ExecutionContext
from kernel.permission_engine.engine import PermissionEngine
from shared.auth.supabase_jwt import verify_supabase_token


class RequestRouter:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._companies = CompanyResolver(pool)
        self._permissions = PermissionEngine(pool)

    async def build_context(
        self,
        *,
        supabase_access_token: str,
        company_id: str | None,
        request_id: str | None,
    ) -> ExecutionContext:
        # 1. Identity - who is this, according to Supabase
        identity = verify_supabase_token(supabase_access_token)

        # 2. Company - which tenant does this request operate within
        company = await self._companies.resolve(identity.user_id, company_id)

        # 3. Permissions - what is this identity allowed to do here
        permissions = await self._permissions.resolve(identity.user_id, company.id)

        return ExecutionContext(
            user_id=identity.user_id,
            email=identity.email,
            company_id=company.id,
            company_name=company.name,
            country=company.country,
            role=permissions.role,
            permissions=permissions.grants,
            request_id=request_id,
        )
