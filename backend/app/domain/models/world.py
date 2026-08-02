"""Domain models representing the World, Chunks, Tiles, and Terrain.

Defines the structure and utility methods for spatial representation in
the simulation engine.
"""

from collections.abc import Generator
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.config import settings


class TerrainType(StrEnum):
    """Enumeration of the basic terrain types in the simulation world."""

    GRASS = "GRASS"
    WATER = "WATER"
    DIRT = "DIRT"
    STONE = "STONE"
    FOREST = "FOREST"
    SAND = "SAND"


class Tile(BaseModel):
    """Represents a single coordinate cell in the simulation grid."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the tile"
    )
    x: int = Field(description="Absolute world X coordinate")
    y: int = Field(description="Absolute world Y coordinate")
    terrain: TerrainType = Field(description="The terrain type of the tile")
    walkable: bool = Field(
        default=True, description="Whether entities can walk on this tile"
    )
    movement_cost: float = Field(
        default=1.0,
        ge=0.0,
        description="Movement speed penalty/bonus multiplier",
    )
    chunk_x: int = Field(description="The X coordinate of the parent chunk")
    chunk_y: int = Field(description="The Y coordinate of the parent chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata for future extensions",
    )

    def serialize(self) -> str:
        """Serializes the Tile into a JSON string.

        Returns:
            JSON string representation of the Tile.
        """
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data_str: str) -> "Tile":
        """Deserializes a JSON string into a Tile instance.

        Args:
            data_str: JSON string.

        Returns:
            Tile instance.
        """
        return cls.model_validate_json(data_str)

    def to_dict(self) -> dict[str, Any]:
        """Converts the Tile to a dictionary.

        Returns:
            Dictionary containing Tile fields.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tile":
        """Creates a Tile instance from a dictionary.

        Args:
            data: Dictionary of fields.

        Returns:
            Tile instance.
        """
        return cls.model_validate(data)


class Chunk(BaseModel):
    """Represents a spatial chunk of tiles in the simulation grid."""

    x: int = Field(description="Chunk X coordinate")
    y: int = Field(description="Chunk Y coordinate")
    tiles: dict[str, Tile] = Field(
        default_factory=dict,
        description="Dictionary mapping 'lx,ly' local coordinate keys to Tile",
    )

    def get_tile(self, local_x: int, local_y: int) -> Tile | None:
        """Retrieves a tile by its local coordinates.

        Args:
            local_x: Local X coordinate (0 to CHUNK_SIZE - 1).
            local_y: Local Y coordinate (0 to CHUNK_SIZE - 1).

        Returns:
            The Tile instance, or None if not found or out of bounds.
        """
        if not (
            0 <= local_x < settings.CHUNK_SIZE and 0 <= local_y < settings.CHUNK_SIZE
        ):
            return None
        return self.tiles.get(f"{local_x},{local_y}")

    def set_tile(self, local_x: int, local_y: int, tile: Tile) -> None:
        """Sets/overwrites a tile at the given local coordinates.

        Args:
            local_x: Local X coordinate.
            local_y: Local Y coordinate.
            tile: The Tile instance to store.
        """
        if not (
            0 <= local_x < settings.CHUNK_SIZE and 0 <= local_y < settings.CHUNK_SIZE
        ):
            raise ValueError(
                f"Local coordinates ({local_x}, {local_y}) are out of bounds."
            )
        self.tiles[f"{local_x},{local_y}"] = tile

    def iterate_tiles(self) -> Generator[Tile, None, None]:
        """Iterates over all tiles currently stored in the chunk.

        Yields:
            Tile instances.
        """
        yield from self.tiles.values()

    def serialize(self) -> str:
        """Serializes the Chunk into a JSON string.

        Returns:
            JSON string representation.
        """
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data_str: str) -> "Chunk":
        """Deserializes a JSON string into a Chunk instance.

        Args:
            data_str: JSON string.

        Returns:
            Chunk instance.
        """
        return cls.model_validate_json(data_str)

    @classmethod
    def create_empty(
        cls,
        chunk_x: int,
        chunk_y: int,
        default_terrain: TerrainType = TerrainType.GRASS,
    ) -> "Chunk":
        """Creates a new Chunk initialized with default tiles.

        Args:
            chunk_x: Chunk X coordinate.
            chunk_y: Chunk Y coordinate.
            default_terrain: Default TerrainType for all tiles.

        Returns:
            A Chunk instance populated with default Tile instances.
        """
        chunk = cls(x=chunk_x, y=chunk_y)
        for lx in range(settings.CHUNK_SIZE):
            for ly in range(settings.CHUNK_SIZE):
                absolute_x = chunk_x * settings.CHUNK_SIZE + lx
                absolute_y = chunk_y * settings.CHUNK_SIZE + ly
                tile = Tile(
                    x=absolute_x,
                    y=absolute_y,
                    terrain=default_terrain,
                    walkable=default_terrain != TerrainType.WATER,
                    movement_cost=1.0,
                    chunk_x=chunk_x,
                    chunk_y=chunk_y,
                )
                chunk.set_tile(lx, ly, tile)
        return chunk


class World(BaseModel):
    """Represents the complete simulation map holding chunks of tiles."""

    chunks: dict[str, Chunk] = Field(
        default_factory=dict,
        description="Dictionary mapping 'cx,cy' coordinate keys to Chunk",
    )

    def create_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
        default_terrain: TerrainType = TerrainType.GRASS,
    ) -> Chunk:
        """Creates and registers a new chunk at the specified coordinates.

        If a chunk already exists, it is returned and not overwritten.

        Args:
            chunk_x: Chunk X coordinate.
            chunk_y: Chunk Y coordinate.
            default_terrain: Default TerrainType for new tiles.

        Returns:
            The created or existing Chunk instance.
        """
        key = f"{chunk_x},{chunk_y}"
        if key in self.chunks:
            return self.chunks[key]

        chunk = Chunk.create_empty(chunk_x, chunk_y, default_terrain)
        self.chunks[key] = chunk
        return chunk

    def retrieve_chunk(self, chunk_x: int, chunk_y: int) -> Chunk | None:
        """Retrieves a chunk by its chunk-space coordinates.

        Args:
            chunk_x: Chunk X coordinate.
            chunk_y: Chunk Y coordinate.

        Returns:
            The Chunk instance, or None if not found.
        """
        return self.chunks.get(f"{chunk_x},{chunk_y}")

    def retrieve_tile(self, x: int, y: int) -> Tile | None:
        """Retrieves a tile by its absolute world-space coordinates.

        Args:
            x: Absolute world X coordinate.
            y: Absolute world Y coordinate.

        Returns:
            The Tile instance, or None if the parent chunk is not created.
        """
        # Calculate parent chunk coordinates using flooring division
        chunk_x = x // settings.CHUNK_SIZE
        chunk_y = y // settings.CHUNK_SIZE

        chunk = self.retrieve_chunk(chunk_x, chunk_y)
        if not chunk:
            return None

        # Calculate local chunk-relative coordinates using modulo
        local_x = x % settings.CHUNK_SIZE
        local_y = y % settings.CHUNK_SIZE

        return chunk.get_tile(local_x, local_y)

    def get_neighbors(
        self, x: int, y: int, include_diagonals: bool = False
    ) -> list[Tile]:
        """Retrieves neighboring tiles in absolute world space.

        Args:
            x: Absolute world X coordinate of the center tile.
            y: Absolute world Y coordinate of the center tile.
            include_diagonals: True to include diagonals, False for cardinal only.

        Returns:
            A list of neighboring Tile instances that exist in the world.
        """
        neighbor_offsets = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
        ]
        if include_diagonals:
            neighbor_offsets.extend(
                [
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                    (-1, -1),
                ]
            )

        neighbors: list[Tile] = []
        for dx, dy in neighbor_offsets:
            tile = self.retrieve_tile(x + dx, y + dy)
            if tile:
                neighbors.append(tile)
        return neighbors

    def serialize(self) -> str:
        """Serializes the entire World state to a JSON string.

        Returns:
            JSON string representation.
        """
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data_str: str) -> "World":
        """Deserializes a JSON string into a World instance.

        Args:
            data_str: JSON string.

        Returns:
            World instance.
        """
        return cls.model_validate_json(data_str)
