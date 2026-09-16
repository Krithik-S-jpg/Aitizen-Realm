"""Tick-driven survival needs and explicit recovery actions."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.calendar import calendar_at_tick
from app.domain.models.entity import Entity
from app.domain.models.structure import StructureType
from app.domain.models.world import TerrainType, World


class NeedsService:
    """Advances living entity needs from world and weather conditions."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes needs against the authoritative world store."""
        self._repository = repository

    def advance_all(self, tick: int) -> None:
        """Advances every active living entity exactly once for a tick."""
        world = self._require_world()
        calendar = calendar_at_tick(tick)
        for structure in world.structures.values():
            if not structure.completed:
                continue
            if structure.structure_type in {
                StructureType.CAMPFIRE,
                StructureType.TORCH,
            }:
                structure.fuel = max(0.0, structure.fuel - 0.25)
            if (
                structure.structure_type == StructureType.FARM
                and structure.crop_food < 12
            ):
                if calendar.temperature_c > 3.0:
                    structure.crop_growth = min(1.0, structure.crop_growth + 1.0 / 72.0)
                if structure.crop_growth >= 1.0:
                    structure.crop_food = 12.0
                    structure.crop_growth = 0.0
        for entity in world.entities.values():
            if not entity.active or entity.needs is None:
                continue
            tile = world.retrieve_tile(entity.x, entity.y)
            local_modifier = 0.0
            if tile is not None:
                climate = float(tile.metadata.get("temperature", 0.5))
                local_modifier = (climate - 0.5) * 10.0
            exposure = 1.0 + calendar.weather_intensity * 0.5
            nearby_structures = [
                structure
                for structure in world.structures.values()
                if structure.completed
                and (structure.x - entity.x) ** 2 + (structure.y - entity.y) ** 2 <= 4
            ]
            sheltered = any(
                structure.structure_type in {StructureType.SHELTER, StructureType.TENT}
                for structure in nearby_structures
            )
            heated = any(
                structure.structure_type
                in {StructureType.CAMPFIRE, StructureType.TORCH}
                and structure.fuel > 0.0
                for structure in nearby_structures
            )
            if sheltered:
                exposure *= 0.35
            local_temperature = calendar.temperature_c + local_modifier
            if heated and local_temperature < 20.0:
                local_temperature = min(20.0, local_temperature + 8.0)
            movement = world.movement_plans.get(str(entity.id))
            exertion = (
                0.65
                if movement is not None and movement.last_advanced_tick == tick
                else 0.0
            )
            entity.needs.advance(local_temperature, exposure, exertion)
            if (sheltered or heated) and entity.needs.body_temperature_c < 37:
                entity.needs.body_temperature_c = min(
                    37.0, entity.needs.body_temperature_c + (0.12 if heated else 0.06)
                )
            if sheltered:
                entity.needs.safety = min(100.0, entity.needs.safety + 0.35)
            if entity.needs.health <= 0.0:
                entity.active = False

    FOOD_EFFECTS = {
        "food": (8.0, 0.0, 0.0),
        "fruit": (12.0, 1.5, 3.0),
        "mushroom": (7.0, 0.0, 0.0),
        "herb": (5.0, 1.0, 0.0),
        "meat": (16.0, 1.0, 0.0),
    }

    def eat(self, entity_id: UUID, amount: float, item_type: str = "food") -> Entity:
        """Consumes a carried edible item and applies its physiological effects."""
        world = self._require_world()
        entity = self._living_entity(world, entity_id)
        if item_type not in self.FOOD_EFFECTS:
            raise ValueError("Item is not edible.")
        inventory = world.inventories[str(entity_id)]
        inventory.consume({item_type: amount})
        nutrition, healing, hydration = self.FOOD_EFFECTS[item_type]
        entity.needs.eat(amount * nutrition, amount * healing)  # type: ignore[union-attr]
        if hydration > 0.0:
            entity.needs.drink(amount * hydration)  # type: ignore[union-attr]
        return entity

    def drink_from_environment(
        self, entity_id: UUID, hydration: float = 35.0
    ) -> Entity:
        """Drinks when standing beside known natural water."""
        world = self._require_world()
        entity = self._living_entity(world, entity_id)
        water_types = {TerrainType.WATER, TerrainType.OCEAN, TerrainType.WETLAND}
        nearby = world.get_neighbors(entity.x, entity.y, include_diagonals=True)
        if not any(tile.terrain in water_types for tile in nearby):
            raise ValueError("Entity is not beside a drinkable water source.")
        entity.needs.drink(hydration)  # type: ignore[union-attr]
        return entity

    def rest(self, entity_id: UUID, recovery: float) -> Entity:
        """Restores energy without advancing simulation time."""
        world = self._require_world()
        entity = self._living_entity(world, entity_id)
        sheltered = any(
            structure.completed
            and structure.structure_type in {StructureType.SHELTER, StructureType.TENT}
            and (structure.x - entity.x) ** 2 + (structure.y - entity.y) ** 2 <= 4
            for structure in world.structures.values()
        )
        entity.needs.rest(recovery * (1.5 if sheltered else 1.0))  # type: ignore[union-attr]
        return entity

    @staticmethod
    def _living_entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        if not entity.active or entity.needs is None:
            raise ValueError("Entity is not an active living entity.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
