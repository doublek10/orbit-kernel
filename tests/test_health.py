"""
Minimal smoke test. Run with: pytest
Requires a reachable Postgres instance matching DATABASE_URL.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/kernel/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "degraded")
