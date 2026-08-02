"""Unit and integration tests for the World System Foundation (RFC-0002)."""

from fastapi.testclient import TestClient

from app.application.services.world_generator import WorldGenerator
from app.application.services.world_service import WorldService
from app.core.config import settings
from app.domain.models.world import TerrainType
from app.domain.utils.coordinates import (
    chunk_to_world,
    local_to_world,
    world_to_chunk,
    world_to_local,
)
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def test_coordinate_utilities() -> None:
    """Tests the two-way conversions between world, chunk, and local spaces."""
    chunk_size = settings.CHUNK_SIZE

    # Positive quadrant test: absolute (18, 5) -> chunk (1, 0), local (2, 5)
    assert world_to_chunk(18, 5) == (1, 0)
    assert world_to_local(18, 5) == (2, 5)
    assert chunk_to_world(1, 0) == (chunk_size, 0)
    assert local_to_world(1, 0, 2, 5) == (18, 5)

    # Negative quadrant test: absolute (-5, -2) -> chunk (-1, -1), local (11, 14)
    # Since -5 // 16 = -1 and -5 % 16 = 11
    assert world_to_chunk(-5, -2) == (-1, -1)
    assert world_to_local(-5, -2) == (11, 14)
    assert chunk_to_world(-1, -1) == (-chunk_size, -chunk_size)
    assert local_to_world(-1, -1, 11, 14) == (-5, -2)


def test_world_generator() -> None:
    """Tests that the WorldGenerator produces a valid 20x20 flat Grass map."""
    world = WorldGenerator.generate_flat_world(20, 20)

    # Spans 4 chunks: (0,0), (1,0), (0,1), (1,1) since CHUNK_SIZE=16
    assert len(world.chunks) == 4
    assert world.retrieve_chunk(0, 0) is not None
    assert world.retrieve_chunk(1, 1) is not None

    # Check tile qualities within boundaries
    for x in range(20):
        for y in range(20):
            tile = world.retrieve_tile(x, y)
            assert tile is not None
            assert tile.x == x
            assert tile.y == y
            assert tile.terrain == TerrainType.GRASS
            assert tile.walkable is True


def test_world_service() -> None:
    """Tests the WorldService lifecycle and repository persistence."""
    repository = InMemoryWorldRepository()
    service = WorldService(repository=repository)

    # Initially empty
    assert service.get_world() is None

    # Create world
    world = service.create_world(20, 20)
    assert world is not None
    assert service.get_world() == world

    # Reset world
    new_world = service.reset_world(10, 10)
    assert new_world is not None
    assert service.get_world() == new_world
    assert new_world != world


def test_world_api_endpoint(api_client: TestClient) -> None:
    """Integration test verifying GET /api/v1/world returns Godot schema."""
    response = api_client.get("/api/v1/world")
    assert response.status_code == 200

    data = response.json()
    assert data["width"] == 20
    assert data["height"] == 20
    assert data["chunk_size"] == settings.CHUNK_SIZE

    tiles = data["tiles"]
    assert len(tiles) == 400

    # Verify formatting: coordinate attributes and lowercase terrain values
    tile_0_0 = tiles[0]
    assert "x" in tile_0_0
    assert "y" in tile_0_0
    assert "terrain" in tile_0_0
    assert tile_0_0["terrain"] == "grass"  # lowercase
