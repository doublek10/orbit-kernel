"""
Orbit Kernel - entrypoint.

Run locally:
    uvicorn main:app --reload --port 60013

Route groups mounted:
- auth_routes: signup/login/refresh/logout - the only place the Kernel
  talks to Supabase.
- routes: identity/resolve + execute - every other authenticated tenant
  request, re-verified fresh every single time (no caching, no
  gateway-side trust).
- admin_routes: the internal Admin Control Panel's API - a fully
  separate authentication system (kernel/admin/auth.py), reachable only
  via the Admin Gateway's own shared secret.
"""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kernel.event_bus.bus import get_event_bus
from kernel.intelligence_engine.observer import subscribe_observer
from kernel.intelligence_engine.scheduler import IntelligenceScheduler
from kernel.kernel_api.admin_routes import admin_router, public_admin_router
from kernel.kernel_api.auth_routes import router as auth_router
from kernel.kernel_api.routes import public_router, router
from kernel.plugin_manager.manager import plugin_manager
from shared import db

logger = logging.getLogger("orbit.kernel")

_intelligence_scheduler: IntelligenceScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await db.connect()
    # Plugin Manager startup sequence: scan country_packages/, read each
    # manifest.py, validate compatibility, register - "Ready" only after
    # this, per the spec's Plugin Manager flow.
    plugin_manager.start()

    # Intelligence Engine: subscribe the Observer to the shared Event
    # Bus ("subscribes to every completed workflow"), then start its own
    # Scheduler for the jobs that run on a clock rather than an event
    # (health/day/week/month/quarter). Both run for the lifetime of the
    # process - "the Intelligence Engine never sleeps".
    global _intelligence_scheduler
    subscribe_observer(pool, get_event_bus(pool))
    _intelligence_scheduler = IntelligenceScheduler(pool)
    _intelligence_scheduler.start()

    yield

    await _intelligence_scheduler.stop()
    await db.disconnect()


app = FastAPI(
    title="Orbit Kernel",
    description="Internal execution engine. Not exposed to the internet.",
    lifespan=lifespan,
)


async def _log_unhandled(request: Request, *, source: str, code: str, message: str) -> None:
    # Fire-and-forget, best-effort: recording the error for the Admin
    # Control Panel must never itself raise, or mask/replace the real
    # response already being returned to the caller.
    try:
        from kernel.admin.error_logger import ErrorLogger
        from shared.db import get_pool

        await ErrorLogger(get_pool()).record(
            source=source,
            code=code,
            message=message,
            request_path=str(request.url.path),
        )
    except Exception:
        pass


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError):
    # A workflow or rule set that genuinely doesn't exist yet returns a
    # clean 501 - never a fake 200, never an opaque 500. The Gateway
    # relies on this exact status to tell the Frontend "not built yet".
    await _log_unhandled(
        request, source="kernel.workflow", code="NOT_IMPLEMENTED", message=str(exc)
    )
    return JSONResponse(status_code=501, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    await _log_unhandled(
        request, source="kernel.validation", code="VALUE_ERROR", message=str(exc)
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Last line of defense: no matter what breaks, the Kernel always
    # returns JSON, never Starlette's default plain-text 500. Every
    # caller (the Gateway, and indirectly the Frontend) unconditionally
    # does response.json() on Kernel responses - a plain-text body here
    # crashes that parse and surfaces as a confusing "Unexpected token"
    # error far from the real cause. The real exception is logged
    # server-side with a full traceback, AND recorded in error_log so
    # the Admin Control Panel's Errors page can surface it; the client
    # only ever gets a generic, safe message, never internal details.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    await _log_unhandled(
        request,
        source="kernel.unhandled",
        code=type(exc).__name__,
        message=str(exc) or "Internal server error",
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(public_router)
app.include_router(router)
app.include_router(auth_router)
app.include_router(public_admin_router)
app.include_router(admin_router)
