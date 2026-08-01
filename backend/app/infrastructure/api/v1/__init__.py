"""V1 API router packaging."""

from app.infrastructure.api.v1.simulation import router as simulation_router

__all__ = ["simulation_router"]
