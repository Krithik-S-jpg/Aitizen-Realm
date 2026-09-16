"""Sustained cross-service acceptance checks using an isolated world."""

from app.application.services.world_service import WorldService
from app.domain.models.cognition import ActionType, TaskStatus
from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import TerrainType
from tests.test_decisions import _systems


def test_agent_survives_and_builds_from_world_resources() -> None:
    """Run 480 ticks without direct action orders or free inventory materials."""
    entities, decisions, _ = _systems()
    repository = decisions._repository  # noqa: SLF001
    world = repository.get()
    assert world is not None
    world.resources.clear()
    water = world.retrieve_tile(5, 6)
    assert water is not None
    water.terrain = TerrainType.WATER
    water.walkable = False
    for kind, x, y in [
        (ResourceType.TREE, 7, 5),
        (ResourceType.STONE, 7, 7),
        (ResourceType.REEDS, 4, 7),
        (ResourceType.BUSH, 4, 4),
    ]:
        node = ResourceNode(
            resource_type=kind,
            x=x,
            y=y,
            quantity=200,
            capacity=200,
            produce_type="fruit" if kind == ResourceType.BUSH else None,
            produce_quantity=100 if kind == ResourceType.BUSH else 0,
            produce_capacity=100 if kind == ResourceType.BUSH else 0,
        )
        world.add_resource(node)
    agent = entities.create(
        EntityKind.AGENT, "Acceptance agent", 5, 5, tags={"autonomous"}
    )
    positions = set()
    for tick in range(480):
        WorldService(repository).advance_resources(tick)
        decisions._navigation.advance_all(tick)  # noqa: SLF001
        decisions._needs.advance_all(tick)  # noqa: SLF001
        decisions.advance_all(tick)
        positions.add((agent.x, agent.y))
        for inventory in world.inventories.values():
            assert inventory.carried <= inventory.capacity
        assert all(node.quantity >= 0 for node in world.resources.values())
    actions = list(world.actions.values())
    completed = {
        action.action_type
        for action in actions
        if action.status == TaskStatus.COMPLETED
    }
    assert agent.active
    assert len(positions) > 3
    assert {
        ActionType.CHOP,
        ActionType.GATHER,
        ActionType.CRAFT,
        ActionType.BUILD,
        ActionType.PLUCK,
        ActionType.EAT,
    } <= completed
    assert any(site.completed for site in world.structures.values())
