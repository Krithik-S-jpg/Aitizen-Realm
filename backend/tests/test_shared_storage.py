"""Communal stockpile conservation and proximity checks."""

import pytest

from app.application.services.construction_service import ConstructionService
from app.domain.models.cognition import ActionType, TaskStatus
from app.domain.models.entity import EntityKind
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
