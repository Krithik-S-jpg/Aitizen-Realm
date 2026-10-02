"""FastAPI router for World monitoring and retrieval.

Provides endpoints to return map dimensions, chunk size, and tiles
to visualization clients such as Godot.
"""

import logging
import secrets
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.application.services.world_service import WorldService
from app.application.services.entity_presentation import activity_details
from app.core.config import settings
from app.domain.models.entity import CitizenAvatar
from app.domain.models.world import World
from app.infrastructure.api.dependencies import get_world_service

logger = logging.getLogger(__name__)

router = APIRouter()
DEFAULT_WORLD_WIDTH = 64
DEFAULT_WORLD_HEIGHT = 64


class TileResponse(BaseModel):
    """Pydantic representation of a formatted world tile for API output."""

    x: int = Field(description="Absolute world X coordinate")
    y: int = Field(description="Absolute world Y coordinate")
    terrain: str = Field(description="Lowercase terrain type name")
    id: UUID = Field(description="Stable tile identifier for this world instance")
    metadata: dict[str, Any] = Field(description="Tile visualization metadata")
    walkable: bool = Field(description="Whether entities may enter the tile")
    movement_cost: float = Field(description="Authoritative traversal cost")


class WorldResponse(BaseModel):
    """Pydantic response schema for Godot client synchronization."""

    width: int = Field(description="Total width of the active simulated map")
    height: int = Field(description="Total height of the active simulated map")
    chunk_size: int = Field(description="The configured size of world chunks")
    seed: int | None = Field(description="Procedural seed, if generated")
    tiles: list[TileResponse] = Field(
        description="Flattened list of tiles matching bounds"
    )
    resources: list[dict[str, Any]] = Field(
        description="Backend-owned harvestable resource nodes"
    )
    structures: list[dict[str, Any]] = Field(
        description="Construction sites and completed structures"
    )
    entities: list[dict[str, Any]] = Field(
        description="Active backend-owned entities visible to the world client"
    )
    schema_version: str = Field(
        default="1.0", description="Version of the client observation contract"
    )
    layer_support: dict[str, str] = Field(
        default_factory=dict,
        description="Authoritative availability of observer map layers",
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
    if not world:
        logger.info(
            "No active world found in repository. Auto-generating default %dx%d map.",
            DEFAULT_WORLD_WIDTH,
            DEFAULT_WORLD_HEIGHT,
        )
        world = world_service.create_world(DEFAULT_WORLD_WIDTH, DEFAULT_WORLD_HEIGHT)

    return _format_world(world)


@router.post("/generate", response_model=WorldResponse)
def generate_world(
    width: int = Query(default=DEFAULT_WORLD_WIDTH, ge=8, le=128),
    height: int = Query(default=DEFAULT_WORLD_HEIGHT, ge=8, le=128),
    seed: int | None = Query(default=None, ge=0, le=2_147_483_647),
    player_avatar: CitizenAvatar = Query(default=CitizenAvatar.SCOUT),
    world_service: WorldService = Depends(get_world_service),
) -> dict[str, Any]:
    """Discards the active world and generates a fresh authoritative world."""
    resolved_seed = seed if seed is not None else secrets.randbelow(2_147_483_648)
    world = world_service.reset_world(width, height, resolved_seed, player_avatar)
    return _format_world(world)


@router.get("/chunk", response_model=dict[str, Any])
def get_or_generate_chunk(
    chunk_x: int = Query(..., ge=-4096, le=4096),
    chunk_y: int = Query(..., ge=-4096, le=4096),
    world_service: WorldService = Depends(get_world_service),
) -> dict[str, Any]:
    """Returns one chunk, generating it deterministically on first access."""
    world = world_service.ensure_chunk(chunk_x, chunk_y)
    chunk = world.retrieve_chunk(chunk_x, chunk_y)
    if chunk is None:
        raise RuntimeError("Chunk generation completed without producing a chunk.")

    tiles = [
        {
            "x": tile.x,
            "y": tile.y,
            "terrain": tile.terrain.value.lower(),
            "id": tile.id,
            "metadata": tile.metadata,
            "walkable": tile.walkable,
            "movement_cost": tile.movement_cost,
        }
        for tile in chunk.iterate_tiles()
    ]
    min_x = chunk_x * settings.CHUNK_SIZE
    min_y = chunk_y * settings.CHUNK_SIZE
    max_x = min_x + settings.CHUNK_SIZE
    max_y = min_y + settings.CHUNK_SIZE
    resources = [
        _format_resource(resource)
        for resource in world.resources.values()
        if min_x <= resource.x < max_x
        and min_y <= resource.y < max_y
        and (not resource.depleted or resource.visual_state in {"fallen", "stump"})
    ]
    structures = [
        _format_structure(structure)
        for structure in world.structures.values()
        if min_x <= structure.x < max_x and min_y <= structure.y < max_y
    ]
    entities = [
        _format_entity(entity, world)
        for entity in world.entities.values()
        if entity.active and min_x <= entity.x < max_x and min_y <= entity.y < max_y
    ]
    return {
        "chunk_x": chunk_x,
        "chunk_y": chunk_y,
        "chunk_size": settings.CHUNK_SIZE,
        "tiles": tiles,
        "resources": resources,
        "structures": structures,
        "entities": entities,
    }


@router.get("/resources", response_model=list[dict[str, Any]])
def get_live_resources(
    world_service: WorldService = Depends(get_world_service),
) -> list[dict[str, Any]]:
    """Returns only live resource state for inexpensive client synchronization."""
    world = world_service.get_world()
    if world is None:
        return []
    return [
        _format_resource(resource)
        for resource in world.resources.values()
        if not resource.depleted or resource.visual_state in {"fallen", "stump"}
    ]


@router.get("/live", response_model=dict[str, Any])
def get_live_scene(
    world_service: WorldService = Depends(get_world_service),
) -> dict[str, Any]:
    """Refreshes changing scene objects without retransmitting terrain tiles."""
    world = world_service.get_world()
    return {
        "resources": get_live_resources(world_service),
        "structures": [_format_structure(item) for item in world.structures.values()]
        if world is not None
        else [],
    }


def _format_world(world: World) -> dict[str, Any]:
    """Formats a domain world for visualization clients."""
    width = world.width or DEFAULT_WORLD_WIDTH
    height = world.height or DEFAULT_WORLD_HEIGHT

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
                        "id": tile.id,
                        "metadata": tile.metadata,
                        "walkable": tile.walkable,
                        "movement_cost": tile.movement_cost,
                    }
                )

    return {
        "schema_version": "1.0",
        "width": width,
        "height": height,
        "chunk_size": settings.CHUNK_SIZE,
        "seed": world.seed,
        "tiles": tiles_list,
        "resources": [
            _format_resource(resource)
            for resource in world.resources.values()
            if not resource.depleted or resource.visual_state in {"fallen", "stump"}
        ],
        "structures": [_format_structure(item) for item in world.structures.values()],
        "entities": [
            _format_entity(entity, world)
            for entity in world.entities.values()
            if entity.active
        ],
        "layer_support": {
            "terrain": "available",
            "resources": "available",
            "population": "available",
            "fertility": "available",
            "temperature": "available",
            "humidity": "available",
            "wealth": "not_implemented",
            "knowledge": "not_implemented",
            "influence": "not_implemented",
            "trade_routes": "not_implemented",
            "danger": "not_implemented",
        },
    }


def _format_resource(resource: Any) -> dict[str, Any]:
    """Formats one backend resource node for Godot."""
    return {
        "id": resource.id,
        "type": resource.resource_type.value.lower(),
        "x": resource.x,
        "y": resource.y,
        "quantity": resource.quantity,
        "capacity": resource.capacity,
        "growth": resource.growth,
        "variant": resource.variant,
        "produce_type": resource.produce_type,
        "produce_quantity": resource.produce_quantity,
        "produce_capacity": resource.produce_capacity,
        "reserved_by": resource.reserved_by,
        "reservation_expires_at": resource.reservation_expires_at,
        "visual_state": resource.visual_state,
        "state_changed_tick": resource.state_changed_tick,
    }


def _format_structure(structure: Any) -> dict[str, Any]:
    """Formats construction state for visualization clients."""
    return {
        **structure.model_dump(mode="json"),
        "structure_type": structure.structure_type.value.lower(),
        "completed": structure.completed,
        "funded": structure.funded,
        "missing_materials": structure.missing_materials,
        "progress_ratio": structure.progress / structure.work_required,
    }


def _format_entity(entity: Any, world: World) -> dict[str, Any]:
    """Formats a moving entity with public survival and activity state."""
    entity_id = str(entity.id)
    active_goal = world.goals.get(world.active_goals.get(entity_id, ""))
    active_action = world.actions.get(world.active_actions.get(entity_id, ""))
    inventory = world.inventories.get(entity_id)
    knowledge = world.entity_knowledge.get(entity_id)
    relationships = sum(
        bond.source_id == entity.id or bond.target_id == entity.id
        for bond in world.social_bonds.values()
    )
    return {
        "id": entity.id,
        "name": entity.name,
        "kind": entity.kind.value.lower(),
        "x": entity.x,
        "y": entity.y,
        "tags": sorted(entity.tags),
        "profession": entity.profession.value.lower(),
        "avatar_id": entity.avatar_id.value,
        "skills": entity.skills,
        "group_id": entity.group_id,
        "perception_radius": entity.perception_radius,
        "knowledge": {
            "tiles": len(knowledge.tiles) if knowledge is not None else 0,
            "resources": len(knowledge.resources) if knowledge is not None else 0,
            "structures": len(knowledge.structures) if knowledge is not None else 0,
            "entities": len(knowledge.entities) if knowledge is not None else 0,
        },
        "memory_count": len(world.episodes.get(entity_id, [])),
        "relationship_count": relationships,
        "needs": entity.needs.model_dump() if entity.needs is not None else None,
        "inventory": inventory.model_dump() if inventory is not None else None,
        "goal": active_goal.goal_type.value.lower()
        if active_goal is not None
        else "idle",
        "action": active_action.action_type.value.lower()
        if active_action is not None
        else str(entity.metadata.get("state", "idle")),
        "action_progress": active_action.progress_ratio
        if active_action is not None
        else 0.0,
        "action_target": active_action.target if active_action is not None else {},
        "decision_reason": active_goal.reason
        if active_goal is not None
        else entity.metadata.get("blocked_reason", ""),
        "metadata": entity.metadata,
        **activity_details(world, entity),
    }
