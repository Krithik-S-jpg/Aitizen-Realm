import pytest

from app.application.services.marine_service import MarineService
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.world import World
from app.domain.models.inventory import Inventory
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository
from tests.test_water_travel import crossing


def test_marine_initialization_is_persistent_and_habitat_constrained():
    world, _, _, decisions = crossing(width=10, ocean=True)
    marine = MarineService(decisions._repository)
    marine.initialize(world)
    nodes = [
        t.metadata["marine"]
        for c in world.chunks.values()
        for t in c.tiles.values()
        if "marine" in t.metadata
    ]
    assert nodes
    nodes[0]["remaining"] = 0
    restored = World.model_validate_json(world.model_dump_json())
    repository = InMemoryWorldRepository()
    repository.save(restored)
    service = MarineService(repository)
    for tick in range(1, 50):
        service.advance_all(tick)
    for entity in restored.entities.values():
        if entity.metadata.get("marine"):
            assert service.wet(restored.retrieve_tile(entity.x, entity.y))
    assert any(
        t.metadata.get("marine", {}).get("remaining") == 0
        for c in restored.chunks.values()
        for t in c.tiles.values()
    )


def test_boat_dive_collect_store_save_and_disembark():
    world, citizen, navigation, decisions = crossing(width=3)
    inventory = world.inventories.setdefault(str(citizen.id), Inventory())
    inventory.add("boat", 1)
    launched = navigation.boat_command(citizen.id, "launch", 0)
    boat = world.entities[launched["id"]]
    assert "boat" not in inventory.items
    navigation.boat_command(citizen.id, "board", 0)
    navigation.boat_command(citizen.id, "row", 0, 4, 7)
    navigation.advance_all(1)
    navigation.advance_all(2)
    assert (boat.x, boat.y) == (citizen.x, citizen.y) == (4, 7)
    assert boat.metadata["anchored"]
    plan = navigation.explore_underwater(citizen.id, 2)
    for tick in range(3, 3 + len(plan.path)):
        navigation.advance_all(tick)
    assert (citizen.x, citizen.y) == (boat.x, boat.y)
    assert not citizen.metadata["underwater"]
    assert citizen.metadata["marine_discoveries"]
    assert sum(inventory.items.values()) > 0
    navigation.boat_command(citizen.id, "store", 10)
    assert world.inventories[str(boat.id)].carried > 0
    restored = World.model_validate_json(world.model_dump_json())
    assert (
        restored.inventories[str(boat.id)].items
        == world.inventories[str(boat.id)].items
    )
    navigation.boat_command(citizen.id, "disembark", 10)
    assert citizen.x == 3
    assert not citizen.metadata["aboard"]
    assert boat.metadata["occupant"] == ""
    cargo_before = world.inventories[str(boat.id)].carried
    navigation.boat_command(citizen.id, "unload", 11)
    assert world.inventories[str(boat.id)].carried == 0
    assert inventory.carried >= cargo_before


def test_predator_hunts_and_fish_flee_without_leaving_water():
    world, _, _, decisions = crossing(width=10, ocean=True)
    service = MarineService(decisions._repository)
    service.initialize(world)
    for entity in world.entities.values():
        if entity.metadata.get("marine"):
            entity.active = False
    shark = Entity(
        kind=EntityKind.ANIMAL,
        name="Shark",
        x=8,
        y=8,
        metadata=dict(marine=True, underwater=True, species="shark", hunger=80),
    )
    fish = Entity(
        kind=EntityKind.ANIMAL,
        name="Fish",
        x=10,
        y=8,
        metadata=dict(
            marine=True, underwater=True, species="reef_fish", hunger=0, school="test"
        ),
    )
    world.entities[str(fish.id)] = fish
    world.entities[str(shark.id)] = shark
    service.advance_all(1)
    assert fish.metadata["state"] == "flee"
    assert shark.metadata["state"] == "hunt"
    position = (fish.x, fish.y)
    service.advance_all(1)
    assert (fish.x, fish.y) == position
    shark.x, shark.y = fish.x, fish.y
    fish.metadata["marine_tick"] = 2
    service.advance_all(2)
    assert not fish.active
    assert shark.metadata["state"] == "feed"


def test_boat_commands_reject_invalid_operations():
    world, citizen, navigation, _ = crossing()
    with pytest.raises(ValueError):
        navigation.boat_command(citizen.id, "launch", 0)
    with pytest.raises(ValueError):
        navigation.boat_command(citizen.id, "store", 0)
    navigation.explore_underwater(citizen.id, 0)
    with pytest.raises(ValueError):
        navigation.boat_command(citizen.id, "board", 0)


def test_expedition_api_commands(api_client):
    from app.infrastructure.api.dependencies import get_navigation_service

    world, citizen, navigation, _ = crossing(width=3)
    inventory = world.inventories.setdefault(str(citizen.id), Inventory())
    inventory.add("wood", 20)
    inventory.add("fiber", 8)
    api_client.app.dependency_overrides[get_navigation_service] = lambda: navigation
    try:
        base = f"/api/v1/entities/{citizen.id}"
        for command in ["craft", "launch", "board"]:
            response = api_client.post(base + "/boat", json={"command": command})
            assert response.status_code == 200, response.text
        assert api_client.post(base + "/dive").status_code == 200
        navigation.advance_all(1)
        assert api_client.post(base + "/dive/return").status_code == 200
        navigation.advance_all(2)
        assert not citizen.metadata["underwater"]
        assert (
            api_client.post(base + "/boat", json={"command": "invalid"}).status_code
            == 409
        )
    finally:
        api_client.app.dependency_overrides.pop(get_navigation_service, None)


def test_capacity_and_important_discovery_memory():
    world, citizen, _, decisions = crossing(width=3)
    service = MarineService(decisions._repository)
    service.initialize(world)
    citizen.x, citizen.y = 4, 5
    tile = world.retrieve_tile(4, 5)
    tile.metadata["marine"].update(landmark="wreck", item="salvage", remaining=3)
    inventory = world.inventories.setdefault(str(citizen.id), Inventory())
    inventory.add("stone", inventory.capacity)
    service.discover_and_collect(world, citizen, 1)
    service.discover_and_collect(world, citizen, 2)
    assert tile.metadata["marine"]["remaining"] == 3
    assert len(world.episodes[str(citizen.id)]) == 1
    inventory.consume({"stone": 1})
    service.discover_and_collect(world, citizen, 3)
    assert inventory.items["salvage"] == 1
    assert tile.metadata["marine"]["remaining"] == 2


def test_mid_dive_checkpoint_continues_to_original_boat():
    from app.application.services.navigation_service import NavigationService

    world, citizen, navigation, _ = crossing(width=3)
    world.inventories.setdefault(str(citizen.id), Inventory()).add("boat", 1)
    navigation.boat_command(citizen.id, "launch", 0)
    navigation.boat_command(citizen.id, "board", 0)
    origin = (citizen.x, citizen.y)
    navigation.explore_underwater(citizen.id, 0)
    navigation.advance_all(1)
    restored = World.model_validate_json(world.model_dump_json())
    repository = InMemoryWorldRepository()
    repository.save(restored)
    resumed = NavigationService(repository)
    for tick in range(2, 10):
        resumed.advance_all(tick)
    diver = restored.entities[str(citizen.id)]
    assert (diver.x, diver.y) == origin
    assert diver.metadata["aboard"]
    assert not diver.metadata["underwater"]
    assert diver.metadata["oxygen"] == 100
