"""World Generator service.

Responsible for generating initial, procedural, or flat worlds for the simulation.
"""

import logging
import math
from uuid import NAMESPACE_URL, uuid5

from app.core.config import settings
from app.domain.models.resource import ResourceNode, ResourceType
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
        world = World(width=width, height=height)

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

    @classmethod
    def generate_terrain_world(
        cls, width: int = 20, height: int = 20, seed: int = 847291
    ) -> World:
        """Generates a deterministic island-like terrain map.

        The implementation uses layered value noise and radial edge falloff. It
        has no external dependency, and the same dimensions and seed always
        produce the same terrain layout.
        """
        logger.info(
            "Generating seeded terrain world %dx%d (seed=%d)...", width, height, seed
        )
        world = World(width=width, height=height, seed=seed)

        for x in range(width):
            for y in range(height):
                terrain, elevation, moisture, temperature = cls._terrain_profile(
                    x, y, seed
                )
                chunk_x = x // settings.CHUNK_SIZE
                chunk_y = y // settings.CHUNK_SIZE
                chunk = world.create_chunk(chunk_x, chunk_y, TerrainType.GRASS)
                tile = Tile(
                    x=x,
                    y=y,
                    terrain=terrain,
                    walkable=terrain not in {TerrainType.WATER, TerrainType.OCEAN},
                    movement_cost=cls._movement_cost(terrain),
                    chunk_x=chunk_x,
                    chunk_y=chunk_y,
                    metadata={
                        "generated": True,
                        "elevation": round(elevation, 3),
                        "moisture": round(moisture, 3),
                        "temperature": round(temperature, 3),
                        "fertility": cls._fertility(
                            terrain, elevation, moisture, temperature
                        ),
                        "variant": int(cls._random_value(x, y, seed + 3501) * 4),
                    },
                )
                chunk.set_tile(x % settings.CHUNK_SIZE, y % settings.CHUNK_SIZE, tile)

                resource = cls._resource_for_tile(x, y, terrain, seed)
                if resource is not None:
                    world.add_resource(resource)

        logger.info("Seeded terrain world generated successfully.")
        return world

    @classmethod
    def generate_chunk(cls, world: World, chunk_x: int, chunk_y: int) -> None:
        """Generates one deterministic chunk if it is not already loaded."""
        if world.retrieve_chunk(chunk_x, chunk_y) is not None:
            return
        if world.seed is None:
            raise ValueError("Chunk generation requires a seeded world.")

        chunk = world.create_chunk(chunk_x, chunk_y, TerrainType.GRASS)
        for local_x in range(settings.CHUNK_SIZE):
            for local_y in range(settings.CHUNK_SIZE):
                x = chunk_x * settings.CHUNK_SIZE + local_x
                y = chunk_y * settings.CHUNK_SIZE + local_y
                terrain, elevation, moisture, temperature = cls._terrain_profile(
                    x, y, world.seed
                )
                tile = Tile(
                    x=x,
                    y=y,
                    terrain=terrain,
                    walkable=terrain not in {TerrainType.WATER, TerrainType.OCEAN},
                    movement_cost=cls._movement_cost(terrain),
                    chunk_x=chunk_x,
                    chunk_y=chunk_y,
                    metadata={
                        "generated": True,
                        "elevation": round(elevation, 3),
                        "moisture": round(moisture, 3),
                        "temperature": round(temperature, 3),
                        "fertility": cls._fertility(
                            terrain, elevation, moisture, temperature
                        ),
                        "variant": int(cls._random_value(x, y, world.seed + 3501) * 4),
                    },
                )
                chunk.set_tile(local_x, local_y, tile)
                resource = cls._resource_for_tile(x, y, terrain, world.seed)
                if resource is not None:
                    world.add_resource(resource)

    @classmethod
    def _resource_for_tile(
        cls, x: int, y: int, terrain: TerrainType, seed: int
    ) -> ResourceNode | None:
        placement = cls._random_value(x, y, seed + 4049)
        resource_type: ResourceType | None = None
        capacity = 0.0

        if terrain == TerrainType.FOREST:
            if placement < 0.24:
                resource_type = ResourceType.TREE
                capacity = 80.0 + cls._random_value(x, y, seed + 4051) * 40.0
            elif placement < 0.29:
                resource_type = ResourceType.BUSH
                capacity = 14.0 + cls._random_value(x, y, seed + 4051) * 12.0
            elif placement < 0.32:
                resource_type = ResourceType.MUSHROOM
                capacity = 5.0 + cls._random_value(x, y, seed + 4051) * 7.0
            elif placement < 0.335:
                resource_type = ResourceType.LOG
                capacity = 28.0 + cls._random_value(x, y, seed + 4051) * 18.0
            elif placement < 0.345:
                resource_type = ResourceType.STUMP
                capacity = 18.0 + cls._random_value(x, y, seed + 4051) * 12.0
        elif terrain in {TerrainType.STONE, TerrainType.MOUNTAIN} and placement < 0.055:
            resource_type = (
                ResourceType.ORE if placement < 0.012 else ResourceType.STONE
            )
            capacity = 70.0 + cls._random_value(x, y, seed + 4057) * 90.0
        elif terrain == TerrainType.TUNDRA and placement < 0.03:
            # Glacially exposed outcrops keep stone available away from ranges.
            resource_type = ResourceType.STONE
            capacity = 55.0 + cls._random_value(x, y, seed + 4057) * 55.0
        elif terrain == TerrainType.GRASS:
            if placement < 0.04:
                resource_type = ResourceType.PLANT
                capacity = 8.0 + cls._random_value(x, y, seed + 4061) * 8.0
            elif placement < 0.065:
                resource_type = ResourceType.BUSH
                capacity = 10.0 + cls._random_value(x, y, seed + 4061) * 10.0
            elif placement < 0.078:
                resource_type = ResourceType.MUSHROOM
                capacity = 4.0 + cls._random_value(x, y, seed + 4061) * 5.0
        elif terrain == TerrainType.WETLAND:
            if placement < 0.09:
                resource_type = ResourceType.REEDS
                capacity = 12.0 + cls._random_value(x, y, seed + 4061) * 12.0
            elif placement < 0.14:
                resource_type = ResourceType.LILY
                capacity = 5.0 + cls._random_value(x, y, seed + 4061) * 6.0
            elif placement < 0.18:
                resource_type = ResourceType.PLANT
                capacity = 8.0 + cls._random_value(x, y, seed + 4061) * 8.0
        elif terrain == TerrainType.WATER and placement < 0.035:
            resource_type = ResourceType.LILY
            capacity = 5.0 + cls._random_value(x, y, seed + 4061) * 6.0
        elif terrain == TerrainType.DIRT and placement < 0.025:
            resource_type = (
                ResourceType.LOG if placement < 0.014 else ResourceType.STUMP
            )
            capacity = 18.0 + cls._random_value(x, y, seed + 4061) * 18.0
        elif terrain == TerrainType.MEADOW:
            if placement < 0.075:
                resource_type = ResourceType.HERB
                capacity = 6.0 + cls._random_value(x, y, seed + 4061) * 8.0
            elif placement < 0.11:
                resource_type = ResourceType.PLANT
                capacity = 8.0 + cls._random_value(x, y, seed + 4061) * 8.0
            elif placement < 0.13:
                resource_type = ResourceType.BUSH
                capacity = 10.0 + cls._random_value(x, y, seed + 4061) * 10.0
        elif terrain == TerrainType.SWAMP:
            if placement < 0.10:
                resource_type = ResourceType.REEDS
                capacity = 12.0 + cls._random_value(x, y, seed + 4061) * 14.0
            elif placement < 0.16:
                resource_type = ResourceType.MUSHROOM
                capacity = 5.0 + cls._random_value(x, y, seed + 4061) * 7.0
            elif placement < 0.20:
                resource_type = ResourceType.HERB
                capacity = 6.0 + cls._random_value(x, y, seed + 4061) * 8.0
        elif terrain in {TerrainType.SAVANNA, TerrainType.DESERT}:
            if placement < 0.045:
                resource_type = ResourceType.CACTUS
                capacity = 18.0 + cls._random_value(x, y, seed + 4061) * 18.0
            elif placement < 0.07:
                resource_type = ResourceType.CLAY
                capacity = 50.0 + cls._random_value(x, y, seed + 4061) * 45.0
        elif terrain == TerrainType.SAND and placement < 0.035:
            resource_type = ResourceType.CLAY
            capacity = 45.0 + cls._random_value(x, y, seed + 4061) * 40.0
        elif terrain == TerrainType.VOLCANIC and placement < 0.08:
            resource_type = ResourceType.ORE if placement < 0.04 else ResourceType.STONE
            capacity = 90.0 + cls._random_value(x, y, seed + 4057) * 110.0

        if resource_type is None:
            return None

        resource_id = uuid5(
            NAMESPACE_URL, f"aitizen-realm:{seed}:{resource_type.value}:{x}:{y}"
        )
        initial_growth = 1.0
        growth_per_tick = 0.0
        regeneration_per_tick = 0.0
        biological_types = {
            ResourceType.TREE,
            ResourceType.PLANT,
            ResourceType.BUSH,
            ResourceType.MUSHROOM,
            ResourceType.REEDS,
            ResourceType.LILY,
            ResourceType.CACTUS,
            ResourceType.HERB,
        }
        if resource_type in biological_types:
            initial_growth = 0.15 + cls._random_value(x, y, seed + 4073) * 0.75
            growth_per_tick = 0.008 if resource_type == ResourceType.TREE else 0.02
            regeneration_per_tick = 0.04 if resource_type == ResourceType.TREE else 0.12
        variant = int(cls._random_value(x, y, seed + 4091) * 4)
        carries_fruit = (
            resource_type == ResourceType.TREE and variant == 2
        ) or resource_type == ResourceType.CACTUS
        return ResourceNode(
            id=resource_id,
            resource_type=resource_type,
            x=x,
            y=y,
            quantity=round(capacity, 2),
            capacity=round(capacity, 2),
            growth=round(initial_growth, 3),
            growth_per_tick=growth_per_tick,
            regeneration_per_tick=regeneration_per_tick,
            variant=variant,
            produce_type="fruit" if carries_fruit else None,
            produce_quantity=round(2.0 + cls._random_value(x, y, seed + 7103) * 5.0, 2)
            if carries_fruit and initial_growth >= 0.65
            else 0.0,
            produce_capacity=8.0 if carries_fruit else 0.0,
            produce_regeneration_per_tick=0.08 if carries_fruit else 0.0,
        )

    @classmethod
    def _terrain_at(cls, x: int, y: int, seed: int) -> TerrainType:
        return cls._terrain_profile(x, y, seed)[0]

    @classmethod
    def _terrain_profile(
        cls, x: int, y: int, seed: int
    ) -> tuple[TerrainType, float, float, float]:
        """Returns a seamless biome plus its deterministic climate values."""
        elevation = (
            cls._value_noise(x * 0.025, y * 0.025, seed) * 0.58
            + cls._value_noise(x * 0.075, y * 0.075, seed + 1013) * 0.29
            + cls._value_noise(x * 0.19, y * 0.19, seed + 1019) * 0.13
        )
        moisture = (
            cls._value_noise(x * 0.035, y * 0.035, seed + 2027) * 0.72
            + cls._value_noise(x * 0.12, y * 0.12, seed + 2039) * 0.28
        )
        temperature = (
            cls._value_noise(x * 0.018, y * 0.018, seed + 3011) * 0.8
            + cls._value_noise(x * 0.09, y * 0.09, seed + 3019) * 0.2
            - max(0.0, elevation - 0.62) * 0.7
        )

        if elevation < 0.24:
            terrain = TerrainType.OCEAN
        elif elevation < 0.30:
            terrain = TerrainType.ICE if temperature < 0.22 else TerrainType.WATER
        elif elevation < 0.35:
            terrain = TerrainType.SAND
        elif elevation > 0.78 and temperature > 0.28:
            terrain = TerrainType.VOLCANIC
        elif elevation > 0.78:
            terrain = TerrainType.MOUNTAIN
        elif elevation > 0.70:
            terrain = TerrainType.STONE
        elif temperature < 0.18:
            terrain = TerrainType.SNOW
        elif temperature < 0.28:
            terrain = TerrainType.TUNDRA
        elif moisture > 0.72 and temperature > 0.30 and elevation < 0.52:
            terrain = TerrainType.SWAMP
        elif moisture > 0.72 and elevation < 0.48:
            terrain = TerrainType.WETLAND
        elif moisture > 0.59:
            terrain = TerrainType.FOREST
        elif moisture < 0.27 and temperature > 0.48:
            terrain = TerrainType.DESERT
        elif temperature > 0.50 and 0.27 <= moisture < 0.48:
            terrain = TerrainType.SAVANNA
        elif moisture < 0.36:
            terrain = TerrainType.DIRT
        elif 0.46 <= moisture < 0.60 and 0.34 <= temperature <= 0.72:
            terrain = TerrainType.MEADOW
        else:
            terrain = TerrainType.GRASS
        return terrain, elevation, moisture, temperature

    @classmethod
    def _value_noise(cls, x: float, y: float, seed: int) -> float:
        x0 = math.floor(x)
        y0 = math.floor(y)
        tx = cls._smoothstep(x - x0)
        ty = cls._smoothstep(y - y0)
        top = cls._lerp(
            cls._random_value(x0, y0, seed),
            cls._random_value(x0 + 1, y0, seed),
            tx,
        )
        bottom = cls._lerp(
            cls._random_value(x0, y0 + 1, seed),
            cls._random_value(x0 + 1, y0 + 1, seed),
            tx,
        )
        return cls._lerp(top, bottom, ty)

    @staticmethod
    def _random_value(x: int, y: int, seed: int) -> float:
        value = (x * 374761393 + y * 668265263 + seed * 1442695041) & 0xFFFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
        value ^= value >> 16
        return value / 0xFFFFFFFF

    @staticmethod
    def _fertility(
        terrain: TerrainType, elevation: float, moisture: float, temperature: float
    ) -> float:
        """Derives soil fertility from authoritative environmental layers."""
        if terrain in {
            TerrainType.OCEAN,
            TerrainType.WATER,
            TerrainType.ICE,
            TerrainType.MOUNTAIN,
            TerrainType.STONE,
            TerrainType.VOLCANIC,
        }:
            return 0.0
        moisture_quality = 1.0 - min(abs(moisture - 0.58) / 0.58, 1.0)
        temperature_quality = 1.0 - min(abs(temperature - 0.52) / 0.52, 1.0)
        elevation_quality = 1.0 - max(0.0, elevation - 0.62) * 1.8
        terrain_factor = {
            TerrainType.FOREST: 1.0,
            TerrainType.GRASS: 0.9,
            TerrainType.WETLAND: 0.72,
            TerrainType.DIRT: 0.55,
            TerrainType.TUNDRA: 0.25,
            TerrainType.SNOW: 0.08,
            TerrainType.SAND: 0.06,
            TerrainType.DESERT: 0.03,
            TerrainType.MEADOW: 1.08,
            TerrainType.SWAMP: 0.62,
            TerrainType.SAVANNA: 0.38,
        }.get(terrain, 0.4)
        return round(
            max(
                0.0,
                min(
                    1.0,
                    moisture_quality
                    * temperature_quality
                    * elevation_quality
                    * terrain_factor,
                ),
            ),
            3,
        )

    @staticmethod
    def _smoothstep(value: float) -> float:
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def _lerp(start: float, end: float, weight: float) -> float:
        return start + (end - start) * weight

    @staticmethod
    def _movement_cost(terrain: TerrainType) -> float:
        return {
            TerrainType.GRASS: 1.0,
            TerrainType.DIRT: 1.1,
            TerrainType.SAND: 1.35,
            TerrainType.FOREST: 1.6,
            TerrainType.STONE: 1.8,
            TerrainType.WATER: 0.0,
            TerrainType.OCEAN: 0.0,
            TerrainType.MOUNTAIN: 3.2,
            TerrainType.DESERT: 1.55,
            TerrainType.TUNDRA: 1.7,
            TerrainType.WETLAND: 2.2,
            TerrainType.SNOW: 1.9,
            TerrainType.ICE: 1.7,
            TerrainType.MEADOW: 0.95,
            TerrainType.SWAMP: 2.6,
            TerrainType.SAVANNA: 1.25,
            TerrainType.VOLCANIC: 2.8,
        }[terrain]
