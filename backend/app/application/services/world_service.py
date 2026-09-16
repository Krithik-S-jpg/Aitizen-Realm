"""World Service class.

Orchestrates the lifecycle, lookup, and generation of the simulation world,
acting as a clean application-level facade.
"""

import logging
from uuid import NAMESPACE_URL, uuid5

from app.application.services.world_generator import WorldGenerator
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.calendar import Season, WeatherType, calendar_at_tick
from app.domain.models.entity import Entity, EntityKind, EntityKnowledge
from app.domain.models.inventory import Inventory
from app.domain.models.needs import NeedsState
from app.domain.models.resource import ResourceType
from app.domain.models.world import Tile, World

logger = logging.getLogger(__name__)


class WorldService:
    """Orchestrates high-level world operations and lifecycle commands."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes the WorldService.

        Args:
            repository: An implementation of IWorldRepository interface.
        """
        self._repository = repository

    def create_world(
        self, width: int = 20, height: int = 20, seed: int = 847291
    ) -> World:
        """Generates and persists a fresh deterministic terrain world.

        Args:
            width: Width of the world in tiles.
            height: Height of the world in tiles.
            seed: Deterministic procedural generation seed.

        Returns:
            The newly created World instance.
        """
        logger.info("Service request: Creating world of size %dx%d...", width, height)
        world = WorldGenerator.generate_terrain_world(width, height, seed)
        self._spawn_animals(world)
        self._spawn_player_agent(world)
        self._repository.save(world)
        return world

    def get_world(self) -> World | None:
        """Retrieves the active simulation world.

        Returns:
            The current active World instance, or None if not set.
        """
        return self._repository.get()

    def reset_world(
        self, width: int = 20, height: int = 20, seed: int = 847291
    ) -> World:
        """Resets the simulation map, purging current state and generating fresh.

        Args:
            width: New world width in tiles.
            height: New world height in tiles.
            seed: Deterministic procedural generation seed.

        Returns:
            The fresh World instance.
        """
        logger.info("Service request: Resetting world...")
        self._repository.delete()
        return self.create_world(width, height, seed)

    def advance_resources(self, tick: int) -> None:
        """Advances all biological resource growth by one simulation tick."""
        world = self._repository.get()
        if world is None:
            return
        calendar = calendar_at_tick(tick)
        weather_multiplier = {
            WeatherType.CLEAR: 0.65,
            WeatherType.RAIN: 1.55,
            WeatherType.SNOW: 0.08,
        }[calendar.weather]
        season_multiplier = {
            Season.SPRING: 1.3,
            Season.SUMMER: 1.0,
            Season.AUTUMN: 0.55,
            Season.WINTER: 0.12,
        }[calendar.season]
        for resource in world.resources.values():
            resource.is_reserved(tick)
            resource.advance_growth(weather_multiplier * season_multiplier)
            if resource.resource_type.value == "TREE":
                if (
                    resource.visual_state == "fallen"
                    and tick - resource.state_changed_tick >= 30
                ):
                    resource.visual_state = "stump"
                    resource.growth = 0.05
                    resource.state_changed_tick = tick
                elif resource.visual_state == "stump" and resource.growth >= 0.30:
                    resource.visual_state = "sapling"
                    resource.state_changed_tick = tick
                elif resource.visual_state == "sapling" and resource.growth >= 0.70:
                    resource.visual_state = "standing"
                    resource.state_changed_tick = tick

    def get_health_snapshot(self) -> dict[str, int | float]:
        """Returns aggregate world health metrics for observers and HUD clients."""
        world = self._repository.get()
        if world is None:
            return {
                "entities": 0,
                "active_entities": 0,
                "citizens": 0,
                "wildlife": 0,
                "resources": 0,
                "depleted_resources": 0,
                "reserved_resources": 0,
                "average_resource_ratio": 0.0,
                "structures": 0,
                "completed_structures": 0,
                "active_goals": 0,
                "active_actions": 0,
                "messages": 0,
                "groups": 0,
            }

        resources = list(world.resources.values())
        resource_ratios = [
            resource.quantity / resource.capacity
            for resource in resources
            if resource.capacity > 0.0
        ]
        structures = list(world.structures.values())
        return {
            "entities": len(world.entities),
            "active_entities": sum(entity.active for entity in world.entities.values()),
            "citizens": sum(
                entity.active and entity.kind == EntityKind.AGENT
                for entity in world.entities.values()
            ),
            "wildlife": sum(
                entity.active and entity.kind == EntityKind.ANIMAL
                for entity in world.entities.values()
            ),
            "resources": len(resources),
            "depleted_resources": sum(resource.depleted for resource in resources),
            "reserved_resources": sum(
                resource.reserved_by is not None for resource in resources
            ),
            "average_resource_ratio": round(
                sum(resource_ratios) / len(resource_ratios), 3
            )
            if resource_ratios
            else 0.0,
            "structures": len(structures),
            "completed_structures": sum(
                structure.completed for structure in structures
            ),
            "active_goals": len(world.active_goals),
            "active_actions": len(world.active_actions),
            "messages": len(world.messages),
            "groups": len(world.groups),
        }

    def ensure_chunk(self, chunk_x: int, chunk_y: int) -> World:
        """Returns the world after ensuring one deterministic chunk exists."""
        world = self._repository.get()
        if world is None:
            world = self.create_world()
        WorldGenerator.generate_chunk(world, chunk_x, chunk_y)
        self._spawn_animals(world, chunk_x, chunk_y)
        return world

    @staticmethod
    def _spawn_animals(
        world: World, chunk_x: int | None = None, chunk_y: int | None = None
    ) -> None:
        """Populates suitable loaded habitats with deterministic wildlife."""
        habitats = {
            "deer": {"forest", "grass", "meadow"},
            "rabbit": {"grass", "meadow", "savanna"},
            "boar": {"forest", "wetland", "swamp"},
            "wolf": {"forest", "mountain", "tundra"},
            "fox": {"forest", "grass", "tundra"},
            "bear": {"forest", "mountain"},
            "goat": {"mountain", "stone", "savanna"},
            "duck": {"wetland", "swamp", "grass"},
        }
        tiles = [
            tile
            for chunk in world.chunks.values()
            if chunk_x is None or (chunk.x == chunk_x and chunk.y == chunk_y)
            for tile in chunk.tiles.values()
            if tile.walkable
        ]
        seed = world.seed or 0

        def suitable_habitat(species: str, tile: Tile) -> bool:
            return species != "duck" or any(
                (water := world.retrieve_tile(x, y)) is not None
                and water.terrain.value.lower() in {"water", "wetland", "swamp"}
                for x in range(tile.x - 3, tile.x + 4)
                for y in range(tile.y - 3, tile.y + 4)
            )

        def add_animal(species: str, tile: Tile) -> None:
            if not suitable_habitat(species, tile):
                return
            animal_id = uuid5(
                NAMESPACE_URL,
                f"aitizen-realm:{seed}:animal:{species}:{tile.x}:{tile.y}",
            )
            key = str(animal_id)
            if key in world.entities:
                return
            animal = Entity(
                id=animal_id,
                kind=EntityKind.ANIMAL,
                name=f"Wild {species.title()}",
                x=tile.x,
                y=tile.y,
                perception_radius=5,
                tags={"wildlife", species},
                metadata={
                    "species": species,
                    "state": "idle",
                    "habitat": tile.terrain.value.lower(),
                    "home_x": tile.x,
                    "home_y": tile.y,
                    "sex": "female" if animal_id.int % 2 == 0 else "male",
                    "age_stage": "adult" if animal_id.int % 5 else "young",
                    "herd_id": f"{species}:{tile.x // 8}:{tile.y // 8}",
                    "foraged": 0.0,
                    "meals": 0,
                    "move_cadence": 1 if species in {"rabbit", "wolf", "fox"} else 2,
                },
                needs=NeedsState(
                    hunger=WorldGenerator._random_value(tile.x, tile.y, seed + 8819)
                    * 35.0
                ),
            )
            world.entities[key] = animal

        for tile in tiles:
            roll = WorldGenerator._random_value(tile.x, tile.y, seed + 8803)
            terrain_name = tile.terrain.value.lower()
            density = 0.010
            if terrain_name in {"mountain", "tundra"}:
                density = 0.001
            elif terrain_name == "stone":
                density = 0.0025
            elif terrain_name in {"wetland", "swamp"}:
                density = 0.014
            if roll >= density:
                continue
            suitable = [
                species
                for species, terrain_names in habitats.items()
                if tile.terrain.value.lower() in terrain_names
                and suitable_habitat(species, tile)
            ]
            if not suitable:
                continue
            species_roll = WorldGenerator._random_value(tile.x, tile.y, seed + 8807)
            rare_roll = WorldGenerator._random_value(tile.x, tile.y, seed + 8811)
            if "bear" in suitable and rare_roll < 0.025:
                species = "bear"
            elif "wolf" in suitable and rare_roll < 0.065:
                species = "wolf"
            elif "fox" in suitable and rare_roll < 0.14:
                species = "fox"
            else:
                common = [
                    species
                    for species in suitable
                    if species not in {"bear", "wolf", "fox"}
                ]
                choices = common or suitable
                species = choices[int(species_roll * len(choices)) % len(choices)]
            add_animal(species, tile)

        if chunk_x is None and chunk_y is None:
            spawned_species = {
                str(entity.metadata.get("species", ""))
                for entity in world.entities.values()
                if entity.kind == EntityKind.ANIMAL
            }
            for species, terrain_names in habitats.items():
                if species in spawned_species:
                    continue
                habitat_tiles = [
                    tile
                    for tile in tiles
                    if tile.terrain.value.lower() in terrain_names
                    and suitable_habitat(species, tile)
                ]
                if not habitat_tiles:
                    continue
                anchor = min(
                    habitat_tiles,
                    key=lambda tile: (
                        WorldGenerator._random_value(
                            tile.x, tile.y, seed + 9901 + len(species)
                        ),
                        tile.y,
                        tile.x,
                    ),
                )
                add_animal(species, anchor)

    @staticmethod
    def _spawn_player_agent(world: World) -> Entity:
        """Creates the single autonomous player-focus agent on a safe central tile."""
        center_x = world.width // 2
        center_y = world.height // 2
        candidates = [
            tile
            for chunk in world.chunks.values()
            for tile in chunk.tiles.values()
            if tile.walkable
        ]
        if not candidates:
            raise RuntimeError("Generated world has no walkable player spawn tile.")
        water_positions = [
            (tile.x, tile.y)
            for chunk in world.chunks.values()
            for tile in chunk.tiles.values()
            if tile.terrain.value in {"WATER", "OCEAN", "WETLAND"}
        ]
        tree_positions = [
            (resource.x, resource.y)
            for resource in world.resources.values()
            if resource.resource_type == ResourceType.TREE
        ]

        def habitat_distance(
            tile_x: int, tile_y: int, points: list[tuple[int, int]]
        ) -> int:
            return min(
                (
                    (tile_x - point_x) ** 2 + (tile_y - point_y) ** 2
                    for point_x, point_y in points
                ),
                default=144,
            )

        spawn = min(
            candidates,
            key=lambda tile: (
                (tile.x - center_x) ** 2
                + (tile.y - center_y) ** 2
                + habitat_distance(tile.x, tile.y, water_positions) * 3
                + habitat_distance(tile.x, tile.y, tree_positions) * 2
                + (
                    0
                    if tile.terrain.value in {"GRASS", "FOREST", "MEADOW", "SAVANNA"}
                    else 420
                ),
                tile.y,
                tile.x,
            ),
        )
        player = Entity(
            kind=EntityKind.AGENT,
            name="Aitizen One",
            x=spawn.x,
            y=spawn.y,
            perception_radius=12,
            tags={"autonomous", "player"},
            needs=NeedsState(),
        )
        key = str(player.id)
        world.entities[key] = player
        world.entity_knowledge[key] = EntityKnowledge(observer_id=player.id)
        world.inventories[key] = Inventory(capacity=60.0)
        world.episodes[key] = []
        return player
