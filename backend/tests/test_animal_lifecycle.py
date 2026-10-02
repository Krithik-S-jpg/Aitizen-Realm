"""Long-lived ecosystem regression tests for births, migration, and death."""

from uuid import UUID

from app.application.services.animal_service import AnimalService
from app.application.services.needs_service import NeedsService
from app.application.services.resource_service import ResourceService
from app.application.services.world_generator import WorldGenerator
from app.application.services.world_service import WorldService
from app.domain.models.calendar import DayPhase, Season
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.inventory import Inventory
from app.domain.models.needs import NeedsState
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import World
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _animal(entity_id: int, species: str, sex: str, x: int = 8, y: int = 8) -> Entity:
    return Entity(
        id=UUID(int=entity_id),
        kind=EntityKind.ANIMAL,
        name=species.title(),
        x=x,
        y=y,
        needs=NeedsState(hunger=10, energy=90, health=100),
        metadata={
            "species": species,
            "sex": sex,
            "age_stage": "adult",
            "age_ticks": 30 * 24,
            "home_x": x,
            "home_y": y,
        },
    )


def _service() -> tuple[AnimalService, World]:
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(16, 16)
    repository.save(world)
    return AnimalService(repository), world


def test_completed_pregnancy_creates_persistent_family() -> None:
    """Healthy parents produce bounded offspring with traceable parentage."""
    service, world = _service()
    mother = _animal(2, "rabbit", "female")
    father = _animal(3, "rabbit", "male", 9, 8)
    mother.metadata.update({"pregnant_since_tick": 0, "mate_id": str(father.id)})
    world.entities = {str(mother.id): mother, str(father.id): father}

    service._advance_life_cycles(world, 5 * 24, Season.SPRING)  # noqa: SLF001

    children = [
        entity
        for entity in world.entities.values()
        if entity.metadata.get("mother_id") == str(mother.id)
    ]
    assert 2 <= len(children) <= 4
    assert all(child.metadata["father_id"] == str(father.id) for child in children)
    assert all(child.metadata["age_stage"] == "young" for child in children)
    assert mother.metadata["offspring_count"] == len(children)


def test_long_days_do_not_accelerate_animal_aging() -> None:
    """Changing clock resolution preserves days lived by wildlife."""
    from app.domain.models.calendar import (
        CalendarControl,
        configure_calendar_control,
        reset_calendar_control,
    )

    service, world = _service()
    deer = _animal(4, "deer", "male")
    world.entities = {str(deer.id): deer}
    configure_calendar_control(0, CalendarControl(ticks_per_day=48))
    try:
        for tick in range(1, 48):
            service.advance_all(tick)
        assert deer.metadata["age_ticks"] == 30 * 24
        service.advance_all(48)
        assert deer.metadata["age_days"] == 31
    finally:
        reset_calendar_control()


def test_local_carrying_capacity_prevents_overpopulation() -> None:
    """Births stop when a habitat patch already supports its configured maximum."""
    service, world = _service()
    mother = _animal(2, "rabbit", "female")
    mother.metadata.update({"pregnant_since_tick": 0, "mate_id": "3"})
    animals = [mother]
    for index in range(3, 24):
        animals.append(_animal(index, "rabbit", "male", 6 + index % 5, 6 + index % 4))
    world.entities = {str(animal.id): animal for animal in animals}

    service._advance_life_cycles(world, 5 * 24, Season.SPRING)  # noqa: SLF001

    assert not any(
        entity.metadata.get("mother_id") == str(mother.id)
        for entity in world.entities.values()
    )


def test_natural_death_creates_finite_decaying_remains() -> None:
    """Death feeds the resource cycle and remains disappear over time."""
    service, world = _service()
    deer = _animal(4, "deer", "female")
    deer.metadata.update({"age_ticks": 500 * 24, "maximum_age_days": 500})
    world.entities = {str(deer.id): deer}

    service._advance_life_cycles(world, 24, Season.SPRING)  # noqa: SLF001

    assert not deer.active
    assert deer.metadata["death_cause"] == "old_age"
    carcass = next(iter(world.resources.values()))
    assert carcass.resource_type == ResourceType.CARCASS
    initial = carcass.quantity
    world_service = WorldService(service._repository)  # noqa: SLF001
    world_service.advance_resources(25)
    assert carcass.quantity < initial
    for tick in range(26, 150):
        world_service.advance_resources(tick)
    assert not world.resources


def test_hungry_animal_migrates_toward_better_habitat() -> None:
    """Failed local feeding selects a persistent, resource-supported destination."""
    service, world = _service()
    deer = _animal(6, "deer", "female", 2, 2)
    deer.needs = NeedsState(hunger=80)
    world.entities = {str(deer.id): deer}
    for x, y in ((11, 10), (12, 10), (11, 11), (12, 11)):
        resource = ResourceNode(
            resource_type=ResourceType.PLANT,
            x=x,
            y=y,
            quantity=20,
            capacity=20,
        )
        world.add_resource(resource)

    assert service._migrate(world, deer, service.PROFILES["deer"], 1)  # noqa: SLF001
    assert deer.metadata["state"] == "migrate"
    assert deer.metadata["migration_reason"] == "food_and_water_pressure"
    assert deer.x > 2 or deer.y > 2


def test_wildlife_routes_around_solid_world_objects() -> None:
    """Movement does not pass through trees and uses a neighbouring route."""
    service, world = _service()
    deer = _animal(8, "deer", "female", 2, 2)
    tree = ResourceNode(
        resource_type=ResourceType.TREE,
        x=3,
        y=2,
        quantity=50,
        capacity=50,
    )
    world.add_resource(tree)

    assert service._step_toward(world, deer, 6, 2, "migrate", 1)  # noqa: SLF001
    assert (deer.x, deer.y) != (3, 2)


def test_carcass_can_be_conserved_as_harvestable_meat() -> None:
    """Animal remains use the same transactional resource system as plants and stone."""
    service, world = _service()
    carcass = ResourceNode(
        resource_type=ResourceType.CARCASS,
        x=5,
        y=5,
        quantity=8,
        capacity=8,
        visual_state="fresh",
    )
    world.add_resource(carcass)
    citizen = Entity(kind=EntityKind.AGENT, name="Scavenger", x=5, y=4)
    world.entities[str(citizen.id)] = citizen
    world.inventories[str(citizen.id)] = Inventory()
    resource_service = ResourceService(service._repository)  # noqa: SLF001
    resource_service.reserve(carcass.id, str(citizen.id), 1, 3)

    _, inventory, gathered = resource_service.gather(carcass.id, str(citizen.id), 3, 1)

    assert gathered == 3
    assert inventory.items == {"meat": 3}
    assert carcass.quantity == 5


def test_hungry_predator_scavenges_before_hunting() -> None:
    """Existing remains satisfy hunger without creating an unnecessary kill."""
    service, world = _service()
    wolf = _animal(20, "wolf", "male", 5, 5)
    wolf.needs = NeedsState(hunger=70)
    rabbit = _animal(21, "rabbit", "female", 6, 5)
    carcass = ResourceNode(
        resource_type=ResourceType.CARCASS,
        x=5,
        y=6,
        quantity=5,
        capacity=5,
        visual_state="fresh",
    )
    world.entities = {str(wolf.id): wolf, str(rabbit.id): rabbit}
    world.add_resource(carcass)

    service._decide(world, wolf, DayPhase.DAWN, Season.SPRING, 2)  # noqa: SLF001

    assert rabbit.active
    assert carcass.quantity == 3
    assert wolf.metadata["state"] == "feed"


def test_parent_has_recovery_interval_between_litters() -> None:
    """A recent birth cannot start another pregnancy on the following day."""
    service, world = _service()
    mother = _animal(30, "rabbit", "female")
    father = _animal(31, "rabbit", "male", 9, 8)
    mother.metadata["last_birth_tick"] = 24
    world.entities = {str(mother.id): mother, str(father.id): father}

    service._advance_life_cycles(world, 48, Season.SPRING)  # noqa: SLF001

    assert "pregnant_since_tick" not in mother.metadata


def test_population_remains_bounded_through_a_breeding_season() -> None:
    """Thirty autonomous days produce offspring without exponential overspawn."""
    service, world = _service()
    mother = _animal(40, "rabbit", "female")
    father = _animal(41, "rabbit", "male", 9, 8)
    world.entities = {str(mother.id): mother, str(father.id): father}
    for x in range(2, 15, 3):
        for y in range(2, 15, 3):
            plant = ResourceNode(
                resource_type=ResourceType.PLANT,
                x=x,
                y=y,
                quantity=30,
                capacity=30,
                regeneration_per_tick=0.08,
            )
            world.add_resource(plant)
    needs = NeedsService(service._repository)  # noqa: SLF001
    world_service = WorldService(service._repository)  # noqa: SLF001
    peak = 2
    births = 0
    for tick in range(30 * 24):
        world_service.advance_resources(tick)
        needs.advance_all(tick)
        service.advance_all(tick)
        active = [
            entity
            for entity in world.entities.values()
            if entity.active and entity.kind == EntityKind.ANIMAL
        ]
        peak = max(peak, len(active))
        births = sum(
            "mother_id" in entity.metadata for entity in world.entities.values()
        )

    assert births > 0
    assert peak <= 24
    assert all(
        entity.needs is None or 0 <= entity.needs.health <= 100
        for entity in world.entities.values()
    )
