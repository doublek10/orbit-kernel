"""
Intelligence Engine - Cache Manager

The Frontend's Intelligence Dashboard is expected to poll
(dashboard.list already works this way). Recomputing balance_summary,
health_score, and every Finding on each poll is wasted work when nothing
has changed - so reads for a given company are cached in-process for a
short TTL, invalidated immediately whenever that company's Intelligence
Cycle actually runs. This is a per-process cache (same limitation the
in-process EventBus and BlueprintLoader caches already have) - fine for
a single Kernel instance, and explicitly not a source of truth: nothing
here is ever read if it isn't in the cache, it's just recomputed.
"""

import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")

_DEFAULT_TTL_SECONDS = 60.0

_cache: dict[str, tuple[float, object]] = {}


async def get_or_compute(key: str, compute: Callable[[], Awaitable[T]], ttl: float = _DEFAULT_TTL_SECONDS) -> T:
    cached = _cache.get(key)
    now = time.monotonic()
    if cached is not None and (now - cached[0]) < ttl:
        return cached[1]  # type: ignore[return-value]

    value = await compute()
    _cache[key] = (now, value)
    return value


def invalidate(company_id: str) -> None:
    for key in [k for k in _cache if k.startswith(f"{company_id}:")]:
        _cache.pop(key, None)
