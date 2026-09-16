"""Solid world resources must constrain authoritative routes."""

from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from tests.test_decisions import _systems


def test_route_avoids_mature_tree_and_opens_after_felling() -> None:
    """Resource depletion changes physical walkability rather than only its art."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Walker", 2, 2)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    tree = ResourceNode(
        resource_type=ResourceType.TREE, x=3, y=2, quantity=20, capacity=20
    )
    world.resources = {str(tree.id): tree}
    decisions._perception.observe(agent.id, 0)  # noqa: SLF001
    navigation = decisions._navigation  # noqa: SLF001
    blocked_route = navigation.plan(agent.id, 4, 2, 0)
    assert (3, 2) not in blocked_route.path
    tree.quantity = 0
    tree.visual_state = "fallen"
    cleared_route = navigation.plan(agent.id, 4, 2, 1)
    assert (3, 2) in cleared_route.path
