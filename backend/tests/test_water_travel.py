import pytest

from app.application.services.navigation_service import NavigationService
from app.application.services.perception_service import PerceptionService
from app.application.services.resource_service import ResourceService
from app.domain.models.entity import EntityKind
from app.domain.models.world import TerrainType, World
from tests.test_decisions import _systems


def crossing(width=2, ocean=False):
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    citizen = entities.create(EntityKind.AGENT, "Explorer", 3, 5, perception_radius=20)
    for x in range(4, 4 + width):
        for y in range(16):
            tile = world.retrieve_tile(x, y)
            tile.terrain = TerrainType.OCEAN if ocean else TerrainType.WATER
            tile.walkable = False
    PerceptionService(decisions._repository).observe(citizen.id, 0)
    return world, citizen, NavigationService(decisions._repository), decisions


def test_short_swim_uses_energy_and_finishes_on_shore_once_per_tick():
    world, citizen, navigation, _ = crossing()
    navigation.plan(citizen.id, 6, 5, 0)
    energy = citizen.needs.energy
    navigation.advance_all(1)
    assert citizen.metadata["travel_mode"] == "swim"
    navigation.advance_all(1)
    assert citizen.needs.energy == energy - 6
    navigation.advance_all(2)
    navigation.advance_all(3)
    assert (citizen.x, citizen.y) == (6, 5)
    assert citizen.metadata["travel_mode"] == "walk"
    assert citizen.needs.energy == energy - 12


def test_tired_and_ocean_swims_rejected():
    _, citizen, navigation, _ = crossing()
    citizen.needs.energy = 35
    with pytest.raises(ValueError):
        navigation.plan(citizen.id, 6, 5, 0)
    _, citizen, navigation, _ = crossing(ocean=True)
    with pytest.raises(ValueError):
        navigation.plan(citizen.id, 6, 5, 0)


def test_crafted_boat_crosses_ocean_and_survives_save():
    world, citizen, navigation, decisions = crossing(width=9, ocean=True)
    resources = ResourceService(decisions._repository)
    inventory = resources.inventory_for(str(citizen.id))
    inventory.add("wood", 20)
    inventory.add("fiber", 8)
    resources.craft(str(citizen.id), "boat")
    navigation.plan(citizen.id, 13, 5, 0)
    navigation.advance_all(1)
    assert citizen.metadata["travel_mode"] == "boat"
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.inventories[str(citizen.id)].items["boat"] == 1
    for tick in range(2, 11):
        navigation.advance_all(tick)
    assert (citizen.x, citizen.y) == (13, 5)
