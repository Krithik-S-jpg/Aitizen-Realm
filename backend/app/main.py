"""Main entry point for Aitizen Realm Backend FastAPI Application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.infrastructure.api.dependencies import get_engine_service, get_event_bus
from app.infrastructure.api.v1.simulation import (
    register_event_broadcaster,
)
from app.infrastructure.api.v1.simulation import (
    router as simulation_router,
)
from app.infrastructure.api.v1.world import router as world_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan context manager for startup and shutdown procedures."""
    # 1. Setup logging
    setup_logging()

    # 2. Register event subscribers (e.g. WebSocket broadcaster)
    event_bus = get_event_bus()
    await register_event_broadcaster(event_bus)

    yield

    # 3. Shutdown cleanup (e.g. stop engine)
    engine_service = get_engine_service()
    await engine_service.stop_simulation()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint returning service identity."""
    return {
        "project": settings.PROJECT_NAME,
        "message": "Welcome to Aitizen Realm Simulation Platform Backend.",
        "status": "online",
    }


app.include_router(
    simulation_router,
    prefix=f"{settings.API_V1_STR}/simulation",
    tags=["simulation"],
)

app.include_router(
    world_router,
    prefix=f"{settings.API_V1_STR}/world",
    tags=["world"],
)
