"""World Service class.

Orchestrates the lifecycle, lookup, and generation of the simulation world,
acting as a clean application-level facade.
"""

import logging

from app.application.services.world_generator import WorldGenerator
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.world import World

logger = logging.getLogger(__name__)


class WorldService:
    """Orchestrates high-level world operations and lifecycle commands."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes the WorldService.

        Args:
            repository: An implementation of IWorldRepository interface.
        """
        self._repository = repository

    def create_world(self, width: int = 20, height: int = 20) -> World:
        """Generates and persists a fresh flat world.

        Args:
            width: Width of the world in tiles.
            height: Height of the world in tiles.

        Returns:
            The newly created World instance.
        """
        logger.info("Service request: Creating world of size %dx%d...", width, height)
        world = WorldGenerator.generate_flat_world(width, height)
        self._repository.save(world)
        return world

    def get_world(self) -> World | None:
        """Retrieves the active simulation world.

        Returns:
            The current active World instance, or None if not set.
        """
        return self._repository.get()

    def reset_world(self, width: int = 20, height: int = 20) -> World:
        """Resets the simulation map, purging current state and generating fresh.

        Args:
            width: New world width in tiles.
            height: New world height in tiles.

        Returns:
            The fresh World instance.
        """
        logger.info("Service request: Resetting world...")
        self._repository.delete()
        return self.create_world(width, height)
