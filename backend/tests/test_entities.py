"""Generic entity and limited-perception system tests."""

import pytest
from fastapi.testclient import TestClient

from app.application.services.entity_service import EntityService
from app.application.services.perception_service import PerceptionService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import CitizenAvatar, EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import Structure, StructureType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _services() -> tuple[EntityService, PerceptionService]:
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(20, 20)
    world.add_resource(
        ResourceNode(
            resource_type=ResourceType.TREE,
            x=6,
            y=5,
            quantity=10.0,
            capacity=10.0,
        )
    )
    world.add_resource(
        ResourceNode(
            resource_type=ResourceType.STONE,
            x=18,
            y=18,
            quantity=10.0,
            capacity=10.0,
        )
    )
    structure = Structure(
        structure_type=StructureType.CAMPFIRE,
        x=5,
        y=6,
        builder_id="setup",
        progress=12.0,
        work_required=12.0,
    )
    world.structures[str(structure.id)] = structure
    repository.save(world)
    return EntityService(repository), PerceptionService(repository)


def test_generic_entity_lifecycle_creates_inventory_and_knowledge() -> None:
    """Entities receive stable supporting state but no autonomous behavior."""
    entities, perception = _services()
    entity = entities.create(EntityKind.AGENT, "Observer", 5, 5, tags={"test"})

    assert entities.get(entity.id) is entity
    assert entities.list_active() == [entity]
    assert perception.knowledge(entity.id).observer_id == entity.id
    assert entities.deactivate(entity.id).active is False
    assert entities.list_active() == []


def test_citizen_avatar_is_persistent_and_validated() -> None:
    """Citizen appearance is authoritative simulation data, not a UI-only choice."""
    entities, _ = _services()
    entity = entities.create(
        EntityKind.AGENT,
        "Mira",
        5,
        5,
        avatar_id=CitizenAvatar.HERBALIST,
    )
    restored = type(entity).model_validate_json(entity.model_dump_json())
    assert restored.avatar_id == CitizenAvatar.HERBALIST


def test_automatic_spawn_avoids_water_and_occupied_tiles() -> None:
    entities, _ = _services()
    world = entities._require_world()
    world.retrieve_tile(5, 5).walkable = False
    with pytest.raises(ValueError, match="walkable"):
        entities.create(EntityKind.AGENT, "Exact", 5, 5)
    first = entities.create(
        EntityKind.AGENT, "Fern", 5, 5,
        avatar_id=CitizenAvatar.HERBALIST, auto_spawn=True,
    )
    second = entities.create(EntityKind.AGENT, "Second", 5, 5, auto_spawn=True)
    assert world.retrieve_tile(first.x, first.y).walkable
    assert (first.x, first.y) != (5, 5)
    assert (first.x, first.y) != (second.x, second.y)
    assert first.avatar_id == CitizenAvatar.HERBALIST


def test_automatic_spawn_fails_without_creating_entity_if_no_land() -> None:
    entities, _ = _services()
    world = entities._require_world()
    for chunk in world.chunks.values():
        for tile in chunk.iterate_tiles():
            tile.walkable = False
    with pytest.raises(ValueError, match="No free walkable tile"):
        entities.create(EntityKind.AGENT, "No land", 5, 5, auto_spawn=True)
    assert entities.list_active() == []


def test_perception_reveals_only_objects_inside_radius() -> None:
    """Observation excludes distant resources and includes nearby world state."""
    entities, perception = _services()
    observer = entities.create(EntityKind.AGENT, "Observer", 5, 5, 2)
    nearby = entities.create(EntityKind.ANIMAL, "Nearby", 6, 6, 2)
    entities.create(EntityKind.OBJECT, "Distant", 15, 15, 2)

    snapshot = perception.observe(observer.id, tick=7)
    assert snapshot["tiles"]
    assert {item["type"] for item in snapshot["resources"]} == {"tree"}
    assert {item["type"] for item in snapshot["structures"]} == {"campfire"}
    assert {item["id"] for item in snapshot["entities"]} == {str(nearby.id)}
    assert all(
        (tile["x"] - observer.x) ** 2 + (tile["y"] - observer.y) ** 2 <= 4
        for tile in snapshot["tiles"]
    )


def test_knowledge_is_private_and_accumulates_last_seen_facts() -> None:
    """Observers retain discoveries without sharing them implicitly."""
    entities, perception = _services()
    first = entities.create(EntityKind.AGENT, "First", 5, 5, 2)
    second = entities.create(EntityKind.AGENT, "Second", 15, 15, 2)

    perception.observe(first.id, tick=3)
    first_knowledge = perception.knowledge(first.id)
    second_knowledge = perception.knowledge(second.id)
    assert first_knowledge.tiles
    assert first_knowledge.resources
    assert second_knowledge.tiles == {}
    assert second_knowledge.resources == {}

    first.x = 18
    first.y = 18
    perception.observe(first.id, tick=9)
    assert {record.data["type"] for record in first_knowledge.resources.values()} == {
        "tree",
        "stone",
    }
    assert (
        min(record.last_seen_tick for record in first_knowledge.resources.values()) == 3
    )


def test_inactive_entity_cannot_observe() -> None:
    """Deactivated identities cannot continue collecting world knowledge."""
    entities, perception = _services()
    observer = entities.create(EntityKind.AGENT, "Observer", 5, 5)
    entities.deactivate(observer.id)
    with pytest.raises(ValueError, match="Inactive"):
        perception.observe(observer.id, tick=1)


def test_entity_and_perception_api_contract(api_client: TestClient) -> None:
    """HTTP routes expose lifecycle, local observation, and private knowledge."""
    world = api_client.post("/api/v1/world/generate?seed=847291").json()
    spawn_tile = next(
        tile for tile in world["tiles"] if tile["terrain"] not in {"water", "ocean"}
    )
    created = api_client.post(
        "/api/v1/entities",
        json={
            "kind": "AGENT",
            "name": "API Observer",
            "x": spawn_tile["x"],
            "y": spawn_tile["y"],
            "perception_radius": 3,
            "avatar_id": "scholar",
        },
    )
    assert created.status_code == 200
    assert created.json()["avatar_id"] == "scholar"
    entity_id = created.json()["id"]

    observed = api_client.post(
        f"/api/v1/entities/{entity_id}/observe", json={"tick": 4}
    )
    assert observed.status_code == 200
    assert observed.json()["radius"] == 3
    assert observed.json()["knowledge_totals"]["tiles"] > 0

    origin = created.json()
    destination = next(
        tile
        for tile in observed.json()["tiles"]
        if tile["walkable"]
        and abs(tile["x"] - origin["x"]) + abs(tile["y"] - origin["y"]) == 1
    )
    route = api_client.post(
        f"/api/v1/entities/{entity_id}/route",
        json={
            "destination_x": destination["x"],
            "destination_y": destination["y"],
            "tick": 4,
        },
    )
    assert route.status_code == 200
    assert route.json()["status"] == "moving"
    api_client.post("/api/v1/simulation/step")
    moved = api_client.get(f"/api/v1/entities/{entity_id}").json()
    assert (moved["x"], moved["y"]) == (destination["x"], destination["y"])
    assert "critical" in moved["needs"]

    knowledge = api_client.get(f"/api/v1/entities/{entity_id}/knowledge")
    assert knowledge.status_code == 200
    assert knowledge.json()["last_observation_tick"] == 4


def test_agent_admin_overview_exposes_operational_details(
    api_client: TestClient,
) -> None:
    """The admin console receives needs, inventory, knowledge, and AI activity."""
    api_client.post("/api/v1/world/generate?seed=847291")
    response = api_client.get("/api/v1/entities/admin/overview")
    assert response.status_code == 200
    player = next(item for item in response.json() if "player" in item["tags"])
    assert player["inventory"]["capacity"] == 60.0
    assert player["needs"]["health"] == 100.0
    assert player["goal"] == "idle"
    assert player["knowledge"] == {
        "tiles": 0,
        "resources": 0,
        "structures": 0,
        "entities": 0,
    }
