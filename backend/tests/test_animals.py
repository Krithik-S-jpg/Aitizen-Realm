"""Tests for species-specific wildlife behavior."""

from uuid import UUID

from app.application.services.animal_service import AnimalService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.domain.models.resource import ResourceNode, ResourceType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def test_killed_animal_cannot_take_a_later_turn_in_same_tick() -> None:
    """The active snapshot must be rechecked after predator interactions."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    wolf = Entity(
        id=UUID(int=4),
        kind=EntityKind.ANIMAL,
        name="Wolf",
        x=3,
        y=3,
        metadata={"species": "wolf", "move_cadence": 2},
        needs=NeedsState(hunger=60),
    )
    deer = Entity(
        id=UUID(int=6),
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=4,
        y=3,
        metadata={"species": "deer", "move_cadence": 2},
        needs=NeedsState(),
    )
    world.entities = {str(wolf.id): wolf, str(deer.id): deer}
    repository.save(world)
    AnimalService(repository).advance_all(0)
    assert not deer.active
    assert (deer.x, deer.y) == (4, 3)
    assert deer.metadata["state"] == "dead"
    assert deer.metadata["killed_by"] == str(wolf.id)


def test_overgrazed_patch_requires_time_to_recover() -> None:
    """Pasture cannot supply unlimited food without ecological recovery."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    world.resources.clear()
    deer = Entity(
        id=UUID(int=6),
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=3,
        y=3,
        metadata={"species": "deer"},
        needs=NeedsState(hunger=60),
    )
    tile = world.retrieve_tile(3, 3)
    assert tile is not None
    tile.metadata.update({"grazing_pressure": 1.0, "last_grazed_tick": 0})
    repository.save(world)
    service = AnimalService(repository)
    assert not service._forage(world, deer, service.PROFILES["deer"], 0)  # noqa: SLF001
    assert deer.needs is not None and deer.needs.hunger == 60
    assert service._forage(world, deer, service.PROFILES["deer"], 90)  # noqa: SLF001
    assert deer.needs.hunger < 60


def test_rabbit_flees_a_nearby_agent() -> None:
    """Prey moves away from citizens inside its species flight distance."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    rabbit = Entity(
        id=UUID(int=2),
        kind=EntityKind.ANIMAL,
        name="Test Rabbit",
        x=3,
        y=3,
        metadata={"species": "rabbit", "move_cadence": 2},
        needs=NeedsState(),
    )
    agent = Entity(kind=EntityKind.AGENT, name="Observer", x=3, y=4)
    world.entities[str(rabbit.id)] = rabbit
    world.entities[str(agent.id)] = agent
    repository.save(world)

    AnimalService(repository).advance_all(tick=2)

    assert rabbit.metadata["state"] == "flee"
    assert (rabbit.x, rabbit.y) != (3, 3)
    assert rabbit.distance_squared_to(agent.x, agent.y) > 1


def test_hungry_deer_seeks_and_consumes_known_food() -> None:
    """A herbivore approaches a valid plant and changes the resource quantity."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    deer = Entity(
        id=UUID(int=3),
        kind=EntityKind.ANIMAL,
        name="Test Deer",
        x=3,
        y=3,
        metadata={"species": "deer", "move_cadence": 3},
        needs=NeedsState(hunger=60.0),
    )
    plant = ResourceNode(
        resource_type=ResourceType.PLANT,
        x=4,
        y=3,
        quantity=5.0,
        capacity=5.0,
    )
    world.entities[str(deer.id)] = deer
    world.add_resource(plant)
    repository.save(world)

    AnimalService(repository).advance_all(tick=3)

    assert deer.metadata["state"] == "graze"
    assert plant.quantity < 5.0
    assert deer.needs is not None and deer.needs.hunger < 60.0


def test_hungry_wolf_hunts_adjacent_deer() -> None:
    """A hungry predator catches nearby valid prey and feeds from the kill."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    wolf = Entity(
        id=UUID(int=4),
        kind=EntityKind.ANIMAL,
        name="Test Wolf",
        x=3,
        y=3,
        metadata={"species": "wolf", "move_cadence": 2, "meals": 0},
        needs=NeedsState(hunger=60.0),
    )
    deer = Entity(
        id=UUID(int=5),
        kind=EntityKind.ANIMAL,
        name="Test Deer",
        x=4,
        y=3,
        metadata={"species": "deer", "move_cadence": 3},
        needs=NeedsState(),
    )
    world.entities[str(wolf.id)] = wolf
    world.entities[str(deer.id)] = deer
    repository.save(world)

    AnimalService(repository).advance_all(tick=2)

    assert wolf.metadata["state"] == "feed"
    assert wolf.metadata["meals"] == 1
    assert not deer.active
    assert wolf.needs is not None and wolf.needs.hunger < 60.0


def test_diurnal_deer_sleeps_at_night() -> None:
    """A satiated diurnal herbivore rests during its inactive night phase."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    deer = Entity(
        id=UUID(int=6),
        kind=EntityKind.ANIMAL,
        name="Sleeping Deer",
        x=3,
        y=3,
        metadata={"species": "deer", "move_cadence": 3},
        needs=NeedsState(hunger=5.0, energy=70.0),
    )
    world.entities[str(deer.id)] = deer
    repository.save(world)

    AnimalService(repository).advance_all(tick=18)

    assert deer.metadata["state"] == "sleep"
    assert deer.needs is not None and deer.needs.energy > 70.0
