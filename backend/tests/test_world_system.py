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


def test_seeded_terrain_generator_is_deterministic() -> None:
    """The same seed produces the same varied terrain layout."""
    first = WorldGenerator.generate_terrain_world(20, 20, seed=847291)
    second = WorldGenerator.generate_terrain_world(20, 20, seed=847291)

    first_terrain = [
        first.retrieve_tile(x, y).terrain
        for x in range(20)
        for y in range(20)  # type: ignore[union-attr]
    ]
    second_terrain = [
        second.retrieve_tile(x, y).terrain
        for x in range(20)
        for y in range(20)  # type: ignore[union-attr]
    ]

    assert first_terrain == second_terrain
    assert len(set(first_terrain)) >= 4
    assert first.seed == 847291


def test_large_world_contains_climate_driven_biomes() -> None:
    """Large maps expose sea, highlands, and climate biome metadata."""
    world = WorldGenerator.generate_terrain_world(128, 128, seed=847291)
    tiles = [tile for chunk in world.chunks.values() for tile in chunk.iterate_tiles()]
    terrains = {tile.terrain for tile in tiles}

    assert TerrainType.OCEAN in terrains
    assert TerrainType.MOUNTAIN in terrains
    assert terrains & {TerrainType.DESERT, TerrainType.TUNDRA, TerrainType.WETLAND}
    assert {
        TerrainType.MEADOW,
        TerrainType.SWAMP,
        TerrainType.SAVANNA,
        TerrainType.VOLCANIC,
    } <= terrains
    assert all(
        {"elevation", "moisture", "temperature", "fertility"} <= tile.metadata.keys()
        for tile in tiles
    )


def test_large_world_contains_diverse_wildlife() -> None:
    """Seeded habitats create prey, predators, grazers, and water birds."""
    repository = InMemoryWorldRepository()
    world = WorldService(repository).create_world(128, 128, seed=847291)
    species = {
        str(entity.metadata.get("species"))
        for entity in world.entities.values()
        if entity.kind.value == "ANIMAL"
    }

    assert {"deer", "rabbit", "boar", "wolf", "fox", "bear", "goat", "duck"} <= species


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
    animals = [
        entity for entity in world.entities.values() if entity.kind.value == "ANIMAL"
    ]
    assert animals
    assert all(entity.metadata.get("species") for entity in animals)

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
    assert data["width"] == 64
    assert data["height"] == 64
    assert data["chunk_size"] == settings.CHUNK_SIZE
    assert data["seed"] == 847291

    tiles = data["tiles"]
    assert len(tiles) == 4096

    # Verify formatting: coordinate attributes and lowercase terrain values
    tile_0_0 = tiles[0]
    assert "x" in tile_0_0
    assert "y" in tile_0_0
    assert "terrain" in tile_0_0
    assert tile_0_0["terrain"] in {terrain.value.lower() for terrain in TerrainType}
    assert "id" in tile_0_0
    assert tile_0_0["metadata"]["generated"] is True
    assert 0.0 <= tile_0_0["metadata"]["fertility"] <= 1.0
    assert "walkable" in tile_0_0
    assert "movement_cost" in tile_0_0

    resources = data["resources"]
    assert resources
    assert {resource["type"] for resource in resources} >= {"tree", "stone"}
    assert all(resource["quantity"] > 0 for resource in resources)


def test_generate_world_api_creates_fresh_seeded_world(
    api_client: TestClient,
) -> None:
    """New-world requests replace the active world and honor explicit settings."""
    response = api_client.post("/api/v1/world/generate?width=12&height=10&seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["width"] == 12
    assert data["height"] == 10
    assert data["seed"] == 42
    assert len(data["tiles"]) == 120

    current = api_client.get("/api/v1/world").json()
    assert current["seed"] == 42


def test_generate_world_api_uses_random_seed(api_client: TestClient) -> None:
    """Omitting a seed generates a new valid random seed."""
    first = api_client.post("/api/v1/world/generate").json()
    second = api_client.post("/api/v1/world/generate").json()
    assert isinstance(first["seed"], int)
    assert isinstance(second["seed"], int)
    assert first["seed"] != second["seed"]


def test_chunk_api_generates_negative_coordinates_deterministically(
    api_client: TestClient,
) -> None:
    """Chunk requests expand the same world into negative coordinate space."""
    api_client.post("/api/v1/world/generate?seed=847291")
    first = api_client.get("/api/v1/world/chunk?chunk_x=-2&chunk_y=3")
    second = api_client.get("/api/v1/world/chunk?chunk_x=-2&chunk_y=3")
    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["tiles"]) == settings.CHUNK_SIZE**2
    assert min(tile["x"] for tile in first.json()["tiles"]) == -32
