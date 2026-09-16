"""Resource-action and construction-system integration tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.application.services.construction_service import ConstructionService
from app.application.services.resource_service import ResourceService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import StructureType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _services() -> tuple[
    ResourceService, ConstructionService, ResourceNode, ResourceNode
]:
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    tree = ResourceNode(
        resource_type=ResourceType.TREE,
        x=1,
        y=1,
        quantity=30.0,
        capacity=30.0,
        regeneration_per_tick=0.5,
    )
    stone = ResourceNode(
        resource_type=ResourceType.STONE,
        x=2,
        y=1,
        quantity=30.0,
        capacity=30.0,
    )
    world.add_resource(tree)
    world.add_resource(stone)
    repository.save(world)
    return ResourceService(repository), ConstructionService(repository), tree, stone


def test_reserve_gather_carry_deplete_and_regenerate() -> None:
    """Resources support their complete transactional lifecycle."""
    resources, _, tree, _ = _services()
    resources.reserve(tree.id, "agent-a", current_tick=5, duration_ticks=3)
    with pytest.raises(ValueError, match="another actor"):
        resources.reserve(tree.id, "agent-b", current_tick=6, duration_ticks=3)

    node, inventory, gathered = resources.gather(tree.id, "agent-a", 50.0, 6)
    assert gathered == 30.0
    assert node.depleted
    assert node.reserved_by is None
    assert inventory.items == {"wood": 30.0}

    node.advance_growth(1.0)
    assert node.quantity == 0.5
    assert not node.depleted


def test_expired_reservation_can_be_reclaimed() -> None:
    """Expired claims cannot permanently lock a resource."""
    resources, _, tree, _ = _services()
    resources.reserve(tree.id, "agent-a", current_tick=2, duration_ticks=2)
    resources.reserve(tree.id, "agent-b", current_tick=4, duration_ticks=2)
    assert tree.reserved_by == "agent-b"


def test_construction_consumes_materials_and_completes() -> None:
    """A paid site accepts collaborative work until completion."""
    resources, construction, tree, stone = _services()
    resources.reserve(tree.id, "builder", 0, 10)
    resources.gather(tree.id, "builder", 5.0, 1)
    resources.reserve(stone.id, "builder", 1, 10)
    resources.gather(stone.id, "builder", 8.0, 2)

    site = construction.place("builder", StructureType.CAMPFIRE, 3, 3)
    assert resources.inventory_for("builder").items == {}
    assert not site.completed
    construction.apply_work(site.id, "builder", 7.0)
    construction.apply_work(site.id, "helper", 10.0)
    assert site.completed
    assert site.progress == site.work_required


def test_actions_api_contract(api_client: TestClient) -> None:
    """Action routes expose reservation, gathering, and blueprints."""
    world = api_client.post("/api/v1/world/generate?seed=847291").json()
    resource_id = world["resources"][0]["id"]
    reservation = api_client.post(
        f"/api/v1/actions/resources/{resource_id}/reserve",
        json={"actor_id": "test-agent", "current_tick": 0, "duration_ticks": 10},
    )
    assert reservation.status_code == 200

    gathered = api_client.post(
        f"/api/v1/actions/resources/{resource_id}/gather",
        json={"actor_id": "test-agent", "current_tick": 1, "amount": 2.0},
    )
    assert gathered.status_code == 200
    assert gathered.json()["gathered"] == 2.0
    assert gathered.json()["inventory"]["carried"] == 2.0
    assert "campfire" in api_client.get("/api/v1/actions/blueprints").json()


def test_missing_action_targets_return_not_found(api_client: TestClient) -> None:
    """Unknown authoritative IDs return a clear not-found response."""
    response = api_client.post(
        f"/api/v1/actions/resources/{uuid4()}/reserve",
        json={"actor_id": "test-agent", "current_tick": 0},
    )
    assert response.status_code == 404


def test_live_scene_matches_world_without_retransmitting_tiles(
    api_client: TestClient,
) -> None:
    """Small live snapshots carry both harvesting and construction state."""
    world = api_client.post("/api/v1/world/generate?seed=847291").json()
    response = api_client.get("/api/v1/world/live")
    assert response.status_code == 200
    assert response.json() == {
        "resources": world["resources"],
        "structures": world["structures"],
    }


def test_actor_can_pluck_fruit_then_chop_tree() -> None:
    """Renewable produce and destructive timber harvesting remain distinct."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    actor = Entity(
        kind=EntityKind.AGENT,
        name="Forager",
        x=2,
        y=2,
        needs=NeedsState(hunger=45.0, health=90.0),
    )
    world.entities[str(actor.id)] = actor
    tree = ResourceNode(
        resource_type=ResourceType.TREE,
        x=3,
        y=2,
        quantity=12.0,
        capacity=12.0,
        growth=1.0,
        growth_per_tick=0.02,
        produce_type="fruit",
        produce_quantity=4.0,
        produce_capacity=6.0,
        produce_regeneration_per_tick=0.2,
    )
    world.add_resource(tree)
    repository.save(world)
    resources = ResourceService(repository)

    _, inventory, plucked = resources.pluck(tree.id, str(actor.id), 2.0)
    assert plucked == 2.0
    assert inventory.items == {"fruit": 2.0}
    assert tree.quantity == 12.0

    _, inventory, chopped = resources.chop(tree.id, str(actor.id), 20.0, 5)
    assert chopped == 12.0
    assert inventory.items == {"fruit": 2.0}
    assert tree.depleted
    assert tree.growth == 1.0  # Preserve the mature silhouette during the fall.
    assert tree.produce_quantity == 0.0
    assert tree.visual_state == "fallen"
    assert tree.state_changed_tick == 5
    timber = [
        node
        for node in world.resources.values()
        if node.resource_type == ResourceType.LOG
    ]
    assert len(timber) == 1
    assert timber[0].quantity == 12.0
    assert (timber[0].x, timber[0].y) == (tree.x, tree.y)
    with pytest.raises(ValueError, match="already been felled"):
        resources.chop(tree.id, str(actor.id), 20.0, 6)
    tree.advance_growth()
    assert tree.quantity == 0.0
    resources.reserve(timber[0].id, str(actor.id), 6, 3)
    resources.gather(timber[0].id, str(actor.id), 12.0, 6)
    assert inventory.items == {"fruit": 2.0, "wood": 12.0}
    assert timber[0].depleted


def test_agent_can_craft_an_axe_and_basket() -> None:
    """Tool recipes consume materials and equipment can improve carrying capacity."""
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(8, 8)
    actor = Entity(kind=EntityKind.AGENT, name="Crafter", x=2, y=2, needs=NeedsState())
    world.entities[str(actor.id)] = actor
    repository.save(world)
    resources = ResourceService(repository)
    inventory = resources.inventory_for(str(actor.id))
    inventory.add("wood", 4.0)
    inventory.add("stone", 3.0)
    inventory.add("fiber", 7.0)

    resources.craft(str(actor.id), "stone_axe")
    old_capacity = inventory.capacity
    resources.craft(str(actor.id), "basket")

    assert inventory.items["stone_axe"] == 1.0
    assert inventory.items["basket"] == 1.0
    assert inventory.capacity == old_capacity + 20.0
