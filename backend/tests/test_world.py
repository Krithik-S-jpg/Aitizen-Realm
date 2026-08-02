"""Unit tests for World, Chunk, Tile, and TerrainType models."""

import pytest

from app.core.config import settings
from app.domain.models.world import Chunk, TerrainType, Tile, World


def test_tile_creation_and_methods() -> None:
    """Tests Tile instantiation, dictionary conversion, and serialization."""
    tile = Tile(
        x=5,
        y=10,
        terrain=TerrainType.STONE,
        walkable=True,
        movement_cost=1.5,
        chunk_x=0,
        chunk_y=0,
        metadata={"elevation": 12},
    )

    # Core properties
    assert tile.x == 5
    assert tile.y == 10
    assert tile.terrain == TerrainType.STONE
    assert tile.walkable is True
    assert tile.movement_cost == 1.5
    assert tile.metadata == {"elevation": 12}

    # Dict Conversion
    t_dict = tile.to_dict()
    assert t_dict["x"] == 5
    assert t_dict["terrain"] == "STONE"

    tile_from_dict = Tile.from_dict(t_dict)
    assert tile_from_dict.id == tile.id
    assert tile_from_dict.movement_cost == 1.5

    # JSON Serialization
    serialized = tile.serialize()
    deserialized = Tile.deserialize(serialized)
    assert deserialized.id == tile.id
    assert deserialized.terrain == TerrainType.STONE
    assert deserialized.metadata == {"elevation": 12}


def test_chunk_creation_empty() -> None:
    """Tests empty Chunk creation and tile grid mapping."""
    chunk = Chunk.create_empty(chunk_x=1, chunk_y=-1, default_terrain=TerrainType.DIRT)

    assert chunk.x == 1
    assert chunk.y == -1

    # Verify tile dimensions and absolute coordinate calculation
    all_tiles = list(chunk.iterate_tiles())
    assert len(all_tiles) == settings.CHUNK_SIZE * settings.CHUNK_SIZE

    # Retrieve specific tiles
    tile_0_0 = chunk.get_tile(0, 0)
    assert tile_0_0 is not None
    assert tile_0_0.x == 1 * settings.CHUNK_SIZE + 0
    assert tile_0_0.y == -1 * settings.CHUNK_SIZE + 0
    assert tile_0_0.terrain == TerrainType.DIRT
    assert tile_0_0.walkable is True

    tile_last = chunk.get_tile(settings.CHUNK_SIZE - 1, settings.CHUNK_SIZE - 1)
    assert tile_last is not None
    assert tile_last.x == 1 * settings.CHUNK_SIZE + (settings.CHUNK_SIZE - 1)
    assert tile_last.y == -1 * settings.CHUNK_SIZE + (settings.CHUNK_SIZE - 1)


def test_chunk_get_set_bounds() -> None:
    """Tests retrieving and setting tiles within Chunk bounds, and error handling."""
    chunk = Chunk.create_empty(chunk_x=0, chunk_y=0)

    # Valid set/get
    new_tile = Tile(
        x=2,
        y=3,
        terrain=TerrainType.SAND,
        chunk_x=0,
        chunk_y=0,
    )
    chunk.set_tile(2, 3, new_tile)
    assert chunk.get_tile(2, 3) == new_tile

    # Out of bounds get returns None
    assert chunk.get_tile(-1, 0) is None
    assert chunk.get_tile(0, settings.CHUNK_SIZE) is None

    # Out of bounds set raises ValueError
    with pytest.raises(ValueError, match="out of bounds"):
        chunk.set_tile(-1, 0, new_tile)


def test_chunk_serialization() -> None:
    """Tests serialization and deserialization of Chunk objects."""
    chunk = Chunk.create_empty(chunk_x=2, chunk_y=2, default_terrain=TerrainType.FOREST)
    serialized = chunk.serialize()
    deserialized = Chunk.deserialize(serialized)

    assert deserialized.x == 2
    assert deserialized.y == 2
    expected_size = settings.CHUNK_SIZE * settings.CHUNK_SIZE
    assert len(list(deserialized.iterate_tiles())) == expected_size
    assert deserialized.get_tile(0, 0).terrain == TerrainType.FOREST


def test_world_operations() -> None:
    """Tests basic world operations: creation, retrieval, and flooring grid lookup."""
    world = World()

    # Create chunk
    chunk = world.create_chunk(0, 0, TerrainType.GRASS)
    assert chunk is not None
    assert len(world.chunks) == 1

    # Retrieving existing chunk returns the same instance without overwriting
    existing = world.create_chunk(0, 0, TerrainType.WATER)
    assert existing == chunk
    assert existing.get_tile(0, 0).terrain == TerrainType.GRASS  # was not overwritten

    # Retrieve chunk
    retrieved = world.retrieve_chunk(0, 0)
    assert retrieved == chunk
    assert world.retrieve_chunk(1, 1) is None


def test_world_coordinate_lookups() -> None:
    """Tests absolute coordinate tile lookups across multiple quadrants."""
    world = World()
    world.create_chunk(0, 0, TerrainType.GRASS)
    world.create_chunk(-1, -1, TerrainType.WATER)

    # Quadrant 1: absolute (5, 5) inside chunk (0, 0)
    tile_pos = world.retrieve_tile(5, 5)
    assert tile_pos is not None
    assert tile_pos.terrain == TerrainType.GRASS
    assert tile_pos.chunk_x == 0
    assert tile_pos.chunk_y == 0

    # Quadrant 3: absolute (-5, -5) inside chunk (-1, -1)
    tile_neg = world.retrieve_tile(-5, -5)
    assert tile_neg is not None
    assert tile_neg.terrain == TerrainType.WATER
    assert tile_neg.chunk_x == -1
    assert tile_neg.chunk_y == -1

    # Not-created chunk lookup returns None
    assert world.retrieve_tile(50, 50) is None


def test_world_neighbor_lookup() -> None:
    """Tests neighbor lookups, including bounds and diagonal settings."""
    world = World()
    # Create adjacent chunks so neighbors exist
    world.create_chunk(0, 0, TerrainType.GRASS)
    world.create_chunk(0, 1, TerrainType.GRASS)
    world.create_chunk(1, 0, TerrainType.GRASS)
    world.create_chunk(1, 1, TerrainType.GRASS)

    # Standard lookup at (5, 5) - cardinal only (4 neighbors)
    cardinal_neighbors = world.get_neighbors(5, 5, include_diagonals=False)
    assert len(cardinal_neighbors) == 4
    # Neighbors of (5,5) are (6,5), (4,5), (5,6), (5,4)
    coords = {(t.x, t.y) for t in cardinal_neighbors}
    assert coords == {(6, 5), (4, 5), (5, 6), (5, 4)}

    # Diagonal lookup - 8 neighbors
    all_neighbors = world.get_neighbors(5, 5, include_diagonals=True)
    assert len(all_neighbors) == 8
    coords_diags = {(t.x, t.y) for t in all_neighbors}
    assert (6, 6) in coords_diags
    assert (4, 4) in coords_diags

    # Boundary lookup - chunk is missing, so only created neighbors are returned
    world_edge = World()
    world_edge.create_chunk(0, 0, TerrainType.GRASS)
    # At (0, 0) absolute, left and bottom neighbors are in
    # (-1, 0) and (0, -1) which do not exist yet.
    edge_neighbors = world_edge.get_neighbors(0, 0, include_diagonals=False)
    assert len(edge_neighbors) == 2  # only (1, 0) and (0, 1) exist
    assert {(t.x, t.y) for t in edge_neighbors} == {(1, 0), (0, 1)}


def test_world_serialization() -> None:
    """Tests entire World state serialization and reconstruction."""
    world = World()
    world.create_chunk(0, 0, TerrainType.GRASS)
    world.create_chunk(-1, 0, TerrainType.STONE)

    # Modify one tile to be sand to verify custom values persist
    tile = world.retrieve_tile(0, 0)
    assert tile is not None
    tile.terrain = TerrainType.SAND

    serialized = world.serialize()
    deserialized = World.deserialize(serialized)

    assert len(deserialized.chunks) == 2
    assert deserialized.retrieve_chunk(0, 0) is not None
    assert deserialized.retrieve_chunk(-1, 0) is not None

    # Check modified tile value
    recon_tile = deserialized.retrieve_tile(0, 0)
    assert recon_tile is not None
    assert recon_tile.terrain == TerrainType.SAND

    # Check stone tile from other chunk
    stone_tile = deserialized.retrieve_tile(-1, 0)
    assert stone_tile is not None
    assert stone_tile.terrain == TerrainType.STONE
