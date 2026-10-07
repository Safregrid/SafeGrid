"""
SafeGrid FastAPI application entry point.

Person 1 owns this file.
Add routers here as subsystems are implemented.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="SafeGrid API",
    description="Disaster preparedness platform — backend API",
    version="0.1.0",
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
