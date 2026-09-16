"""Survival needs and authoritative navigation tests."""

import pytest

from app.application.services.entity_service import EntityService
from app.application.services.navigation_service import NavigationService
from app.application.services.needs_service import NeedsService
from app.application.services.perception_service import PerceptionService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import EntityKind
from app.domain.models.navigation import MovementStatus
from app.domain.models.needs import NeedsState
from app.domain.models.world import TerrainType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _systems() -> tuple[
    EntityService, PerceptionService, NeedsService, NavigationService
]:
    repository = InMemoryWorldRepository()
    repository.save(WorldGenerator.generate_flat_world(16, 16))
    return (
        EntityService(repository),
        PerceptionService(repository),
        NeedsService(repository),
        NavigationService(repository),
    )


def test_needs_advance_with_time_environment_and_exertion() -> None:
    """Living needs degrade predictably while objects remain unaffected."""
    entities, perception, needs, navigation = _systems()
    agent = entities.create(EntityKind.AGENT, "Walker", 5, 5, 5)
    object_entity = entities.create(EntityKind.OBJECT, "Crate", 8, 8)
    perception.observe(agent.id, 0)
    navigation.plan(agent.id, 7, 5, 0)
    navigation.advance_all(1)
    needs.advance_all(1)

    assert agent.needs is not None
    assert agent.needs.hunger > 0.16
    assert agent.needs.thirst > 0.24
    assert agent.needs.energy < 99.9
    assert object_entity.needs is None


def test_eating_drinking_and_resting_restore_needs() -> None:
    """Explicit survival actions consume resources and restore state."""
    entities, _, needs, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Survivor", 5, 5)
    assert agent.needs is not None
    agent.needs.hunger = 70.0
    agent.needs.thirst = 70.0
    agent.needs.energy = 20.0
    world = needs._repository.get()  # noqa: SLF001
    assert world is not None
    world.inventories[str(agent.id)].add("food", 4.0)
    water = world.retrieve_tile(6, 5)
    assert water is not None
    water.terrain = TerrainType.WATER
    water.walkable = False

    needs.eat(agent.id, 2.0)
    needs.drink_from_environment(agent.id, 30.0)
    needs.rest(agent.id, 25.0)
    assert agent.needs.hunger == 54.0
    assert agent.needs.thirst == 40.0
    assert agent.needs.energy == 45.0
    assert world.inventories[str(agent.id)].items["food"] == 2.0


def test_navigation_uses_known_tiles_and_advances_one_step_per_tick() -> None:
    """A route never teleports and cannot use undiscovered world state."""
    entities, perception, _, navigation = _systems()
    agent = entities.create(EntityKind.AGENT, "Explorer", 5, 5, 4)
    with pytest.raises(ValueError, match="outside"):
        navigation.plan(agent.id, 7, 5, 0)

    perception.observe(agent.id, 0)
    plan = navigation.plan(agent.id, 8, 5, 0)
    assert plan.path[0] == (5, 5)
    assert plan.path[-1] == (8, 5)
    assert (agent.x, agent.y) == (5, 5)

    navigation.advance_all(1)
    assert (agent.x, agent.y) == (6, 5)
    assert plan.status == MovementStatus.MOVING
    navigation.advance_all(2)
    navigation.advance_all(3)
    assert (agent.x, agent.y) == (8, 5)
    assert plan.status == MovementStatus.ARRIVED
    assert plan.remaining_steps == 0


def test_navigation_rejects_unwalkable_destination() -> None:
    """Backend routing refuses known water destinations."""
    entities, perception, _, navigation = _systems()
    agent = entities.create(EntityKind.AGENT, "Explorer", 5, 5, 3)
    world = navigation._repository.get()  # noqa: SLF001
    assert world is not None
    destination = world.retrieve_tile(6, 5)
    assert destination is not None
    destination.terrain = TerrainType.WATER
    destination.walkable = False
    perception.observe(agent.id, 0)
    with pytest.raises(ValueError, match="not walkable"):
        navigation.plan(agent.id, 6, 5, 0)


def test_starvation_damages_health_and_fruit_supports_recovery() -> None:
    """Severe unmet needs cause damage while nutritious food can restore health."""
    needs = NeedsState(hunger=99.0, thirst=99.0, health=70.0)
    needs.advance(20.0)
    assert needs.health < 70.0
    damaged_health = needs.health
    needs.eat(30.0, healing=4.0)
    assert needs.hunger < 99.0
    assert needs.health > damaged_health
