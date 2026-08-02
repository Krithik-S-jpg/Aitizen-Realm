"""FastAPI router for World monitoring and retrieval.

Provides endpoints to return map dimensions, chunk size, and tiles
to visualization clients such as Godot.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.application.services.world_service import WorldService
from app.core.config import settings
from app.infrastructure.api.dependencies import get_world_service

logger = logging.getLogger(__name__)

router = APIRouter()


class TileResponse(BaseModel):
    """Pydantic representation of a formatted world tile for API output."""

    x: int = Field(description="Absolute world X coordinate")
    y: int = Field(description="Absolute world Y coordinate")
    terrain: str = Field(description="Lowercase terrain type name")


class WorldResponse(BaseModel):
    """Pydantic response schema for Godot client synchronization."""

    width: int = Field(description="Total width of the active simulated map")
    height: int = Field(description="Total height of the active simulated map")
    chunk_size: int = Field(description="The configured size of world chunks")
    tiles: list[TileResponse] = Field(
        description="Flattened list of tiles matching bounds"
    )


@router.get("", response_model=WorldResponse)
def get_world(
    world_service: WorldService = Depends(get_world_service),
) -> dict[str, Any]:
    """Retrieves the active simulation world grid, generating a default if needed.

    Returns:
        A formatted JSON payload with map details and tile listings.
    """
    world = world_service.get_world()
    width = 20
    height = 20

    if not world:
        logger.info(
            "No active world found in repository. Auto-generating default %dx%d map.",
            width,
            height,
        )
        world = world_service.create_world(width, height)

    # Flatten and format all tiles within the 20x20 boundaries
    tiles_list: list[dict[str, Any]] = []
    for x in range(width):
        for y in range(height):
            tile = world.retrieve_tile(x, y)
            if tile:
                tiles_list.append(
                    {
                        "x": tile.x,
                        "y": tile.y,
                        "terrain": tile.terrain.value.lower(),
                    }
                )

    return {
        "width": width,
        "height": height,
        "chunk_size": settings.CHUNK_SIZE,
        "tiles": tiles_list,
    }
