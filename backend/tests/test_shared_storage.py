"""Communal stockpile conservation and proximity checks."""

import pytest

from app.application.services.construction_service import ConstructionService
from app.domain.models.cognition import ActionType, TaskStatus
from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import Structure, StructureType
from tests.test_decisions import _systems


def test_two_citizens_share_materials_without_creating_resources() -> None:
    """One citizen's deposit is another citizen's withdrawal, with bounded capacity."""
    entities, decisions, _ = _systems()
    first = entities.create(EntityKind.AGENT, "Depositor", 5, 5)
    second = entities.create(EntityKind.AGENT, "Builder", 5, 5)
    repository = decisions._repository  # noqa: SLF001
    world = repository.get()
    assert world is not None
    store = Structure(
        structure_type=StructureType.STORAGE,
        x=6,
        y=5,
        builder_id=str(first.id),
        work_required=1,
        progress=1,
    )
    world.structures[str(store.id)] = store
    world.inventories[str(first.id)].add("wood", 20)
    service = ConstructionService(repository)
    assert service.transfer_storage(store.id, str(first.id), "wood", 15) == 15
    assert service.transfer_storage(store.id, str(second.id), "wood", 10, True) == 10
    assert store.stockpile.items["wood"] == 5
    assert world.inventories[str(first.id)].items["wood"] == 5
    assert world.inventories[str(second.id)].items["wood"] == 10
    second.x = 1
    with pytest.raises(ValueError, match="beside"):
        service.transfer_storage(store.id, str(second.id), "wood", 5, True)
    assert store.stockpile.items["wood"] == 5
    first_pack = world.inventories[str(first.id)]
    first_pack.capacity = first_pack.carried + 2
    assert service.transfer_storage(store.id, str(first.id), "wood", 5, True) == 2
    assert store.stockpile.items["wood"] == 3
    with pytest.raises(ValueError, match="finite"):
        service.transfer_storage(store.id, str(first.id), "wood", float("nan"))


def test_citizen_walks_to_known_storage_for_recipe_material() -> None:
    """Utility AI selects storage and transfers only after arriving beside it."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Runner", 3, 3, tags={"autonomous"})
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    world.resources.clear()
    store = Structure(
        structure_type=StructureType.STORAGE,
        x=6,
        y=3,
        builder_id=str(agent.id),
        work_required=1,
        progress=1,
    )
    store.stockpile.add("wood", 10)
    store.stockpile.add("stone", 10)
    world.structures[str(store.id)] = store
    _, action = decisions.decide(agent.id, 0)
    assert action.action_type == ActionType.MOVE
    assert action.target["storage_id"] == str(store.id)
    assert world.inventories[str(agent.id)].carried == 0
    for tick in range(1, 12):
        decisions._navigation.advance_all(tick)  # noqa: SLF001
        decisions.advance_all(tick)
        if action.status == TaskStatus.COMPLETED:
            break
    assert action.status == TaskStatus.COMPLETED
    assert abs(agent.x - store.x) + abs(agent.y - store.y) == 1
    assert world.inventories[str(agent.id)].carried > 0
    assert world.inventories[str(agent.id)].carried + store.stockpile.carried == 20


def test_tree_to_ground_log_to_storage_to_finished_shelter() -> None:
    """Timber crosses real world and inventory boundaries exactly once."""
    entities, decisions, _ = _systems()
    harvester = entities.create(EntityKind.AGENT, "Harvester", 5, 5)
    builder = entities.create(EntityKind.AGENT, "Builder", 5, 5)
    world = decisions._require_world()  # noqa: SLF001
    resources = decisions._resources  # noqa: SLF001
    construction = decisions._construction  # noqa: SLF001
    tree = ResourceNode(
        resource_type=ResourceType.TREE, x=6, y=5, quantity=30, capacity=30
    )
    world.add_resource(tree)
    resources.chop(tree.id, str(harvester.id), 30, 1)
    timber = next(
        node
        for node in world.resources.values()
        if node.resource_type == ResourceType.LOG
    )
    assert world.inventories[str(harvester.id)].carried == 0
    assert tree.visual_state == "fallen" and timber.quantity == 30
    resources.reserve(timber.id, str(harvester.id), 2, 10)
    resources.gather(timber.id, str(harvester.id), 20, 2)
    store = Structure(
        structure_type=StructureType.STORAGE,
        x=5,
        y=6,
        builder_id=str(builder.id),
        work_required=1,
        progress=1,
    )
    world.structures[str(store.id)] = store
    construction.transfer_storage(store.id, str(harvester.id), "wood", 20)
    construction.transfer_storage(store.id, str(builder.id), "wood", 20, True)
    stone = ResourceNode(
        resource_type=ResourceType.STONE, x=4, y=5, quantity=5, capacity=5
    )
    world.add_resource(stone)
    resources.reserve(stone.id, str(builder.id), 3, 10)
    resources.gather(stone.id, str(builder.id), 5, 3)
    site = construction.place(str(builder.id), StructureType.SHELTER, 5, 4)
    assert world.inventories[str(builder.id)].carried == 0
    assert store.stockpile.carried == 0
    while not site.completed:
        construction.apply_work(site.id, str(builder.id), 2)
    assert site.completed and stone.depleted
    assert timber.quantity == 10
