"""
SafeGrid FastAPI application entry point.

Person 1 owns this file.
Add routers here as subsystems are implemented.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import init_db
from app.ingestion.grid_run import run_grid_from_settings

logging.basicConfig(
    level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("safegrid.grid")


async def _grid_refresh_loop() -> None:
    """
    Keeps the regional grid fresh on a timer.

    Runs immediately, then sleeps. Every failure is logged and retried after
    the interval rather than killing the loop: one unreachable weather API
    must not leave every cell reading as stale until someone notices. This is
    the behaviour half of task 2 — run_grid() alone is only the capability.
    """
    while True:
        try:
            report = await run_grid_from_settings()
        except Exception:
            logger.exception(
                "grid refresh failed; retrying in %s min", settings.grid_run_minutes
            )
        else:
            log = logger.warning if not report.complete else logger.info
            log(
                "grid refresh: %s/%s cells stored for %s (generated_at %s)",
                report.written_cells,
                report.planned_cells,
                report.region_name,
                report.generated_at,
            )
            if report.cells_below_window:
                logger.warning(
                    "%s cells returned less than %s hours of forecast",
                    report.cells_below_window,
                    settings.grid_window_hours,
                )
        await asyncio.sleep(settings.grid_run_minutes * 60)


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    # init_db() belongs here: nothing else created the tables, so a fresh
    # clone (or CI) failed on "no such table" until someone ran a test.
    init_db()

    task: asyncio.Task[None] | None = None
    if settings.grid_scheduler_enabled:
        # create_task, not await: startup must not block on a network call.
        task = asyncio.create_task(_grid_refresh_loop())
        logger.info(
            "grid scheduler: every %s min over region %s",
            settings.grid_run_minutes,
            settings.grid_region_name,
        )

    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="SafeGrid API",
    description="Disaster preparedness platform — backend API",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Health check endpoint. Returns 200 when the backend is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Register routers below as they are implemented.
# Example:
#   from app.api import hazards, risk_zones
#   app.include_router(hazards.router, prefix="/api")
#   app.include_router(risk_zones.router, prefix="/api")
# ---------------------------------------------------------------------------

from app.api.data import router as data_router
from app.api.hazards import router as hazards_router
from app.api.risk import router as risk_router
from app.api.risk_zones import router as risk_zones_router

app.include_router(data_router, prefix="/api")
app.include_router(hazards_router, prefix="/api")
app.include_router(risk_zones_router, prefix="/api")
app.include_router(risk_router, prefix="/api")


