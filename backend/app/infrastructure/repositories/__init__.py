"""Infrastructure repository adapters."""

from app.infrastructure.repositories.world_repository import (
    InMemoryWorldRepository,
)

__all__ = ["InMemoryWorldRepository"]
