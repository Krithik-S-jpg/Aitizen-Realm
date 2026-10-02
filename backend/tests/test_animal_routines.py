"""Individual comfort routines retain survival priority."""

from uuid import UUID

from app.application.services.animal_service import AnimalService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.calendar import DayPhase, Season
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.domain.models.world import TerrainType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def test_deer_ruminates_when_safe_but_hunger_preempts_comfort() -> None:
    """Comfort restores energy, but is not a script overriding hunger."""
    world = WorldGenerator.generate_flat_world(8, 8)
    world.resources.clear()
    repository = InMemoryWorldRepository()
    repository.save(world)
    deer = Entity(
        id=UUID(int=11),
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=3,
        y=3,
        metadata={"species": "deer"},
        needs=NeedsState(energy=70),
    )
    world.entities[str(deer.id)] = deer
    service = AnimalService(repository)
    service._decide(world, deer, DayPhase.DAY, Season.SPRING, 0)
    assert deer.metadata["state"] == "ruminate"
    assert deer.needs.energy == 72
    deer.needs.hunger = 90
    service._decide(world, deer, DayPhase.DAY, Season.SPRING, 11)
    assert deer.metadata["state"] != "ruminate"
    assert deer.metadata["feeding_threshold"] == 18


def test_predator_interrupts_weather_shelter() -> None:
    """A deer cannot ignore a predator just because the weather is bad."""
    world = WorldGenerator.generate_flat_world(8, 8)
    world.retrieve_tile(3, 3).terrain = TerrainType.FOREST
    repository = InMemoryWorldRepository()
    repository.save(world)
    deer = Entity(
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=3,
        y=3,
        metadata={"species": "deer", "weather_intensity": 0.9},
        needs=NeedsState(),
    )
    wolf = Entity(
        kind=EntityKind.ANIMAL,
        name="Wolf",
        x=2,
        y=3,
        metadata={"species": "wolf"},
        needs=NeedsState(),
    )
    world.entities = {str(deer.id): deer, str(wolf.id): wolf}
    AnimalService(repository)._decide(world, deer, DayPhase.NIGHT, Season.SPRING, 20)
    assert deer.metadata["state"] == "flee"
    assert (deer.x, deer.y) != (3, 3)


def test_dehydration_interrupts_exhaustion_rest() -> None:
    """An exhausted animal still drinks when dangerously dehydrated."""
    world = WorldGenerator.generate_flat_world(8, 8)
    world.retrieve_tile(3, 4).terrain = TerrainType.WATER
    repository = InMemoryWorldRepository()
    repository.save(world)
    deer = Entity(
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=3,
        y=3,
        metadata={"species": "deer"},
        needs=NeedsState(thirst=90, energy=10),
    )
    world.entities[str(deer.id)] = deer
    AnimalService(repository)._decide(world, deer, DayPhase.NIGHT, Season.SPRING, 20)
    assert deer.metadata["state"] == "drink"
    assert deer.needs.thirst < 90


def test_displaced_duck_returns_toward_water_without_being_thirsty() -> None:
    world = WorldGenerator.generate_flat_world(16, 16)
    world.retrieve_tile(10, 5).terrain = TerrainType.WATER
    repository = InMemoryWorldRepository()
    repository.save(world)
    duck = Entity(kind=EntityKind.ANIMAL, name="Duck", x=5, y=5,
                  metadata={"species": "duck"}, needs=NeedsState())
    world.entities[str(duck.id)] = duck
    service = AnimalService(repository)
    before = duck.distance_squared_to(10, 5)
    service._decide(world, duck, DayPhase.DAY, Season.SPRING, 1)
    assert duck.distance_squared_to(10, 5) < before
    assert duck.metadata["state"] == "seek_water"
    assert "shoreline" in duck.metadata["behavior_reason"]
    assert duck.metadata["movement_target"] == [10, 5]
