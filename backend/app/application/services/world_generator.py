"""World Generator service.

Responsible for generating initial, procedural, or flat worlds for the simulation.
"""

import logging

from app.core.config import settings
from app.domain.models.world import TerrainType, Tile, World

logger = logging.getLogger(__name__)


class WorldGenerator:
    """Generates world simulation maps based on specified rules."""

    @staticmethod
    def generate_flat_world(width: int = 20, height: int = 20) -> World:
        """Generates a flat world of all GRASS tiles of specified size.

        Args:
            width: Width of the world in tiles (default 20).
            height: Height of the world in tiles (default 20).

        Returns:
            A populated World instance.
        """
        logger.info(
            "Generating flat world of size %dx%d with default GRASS terrain...",
            width,
            height,
        )
        world = World()

        # Iterate over the bounds to determine and populate the necessary chunks
        for x in range(width):
            for y in range(height):
                chunk_x = x // settings.CHUNK_SIZE
                chunk_y = y // settings.CHUNK_SIZE

                # Ensure chunk is created in the world (defaults to GRASS already)
                chunk = world.create_chunk(chunk_x, chunk_y, TerrainType.GRASS)

                # Ensure individual tile is set correctly
                local_x = x % settings.CHUNK_SIZE
                local_y = y % settings.CHUNK_SIZE

                tile = Tile(
                    x=x,
                    y=y,
                    terrain=TerrainType.GRASS,
                    walkable=True,
                    movement_cost=1.0,
                    chunk_x=chunk_x,
                    chunk_y=chunk_y,
                )
                chunk.set_tile(local_x, local_y, tile)

        logger.info("Flat world generated successfully.")
        return world
