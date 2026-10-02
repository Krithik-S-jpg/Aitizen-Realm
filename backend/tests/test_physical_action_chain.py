"""Cross-system regressions: reach, dropped timber, storage and restoring depletion."""

import pytest

from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_decisions import _systems


def test_tree_to_storage_to_shelter_survives_save_load() -> None:
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    citizen = entities.create(EntityKind.AGENT, "Carrier", 5, 5)
    actor = str(citizen.id)
    resources = decisions._resources
    tree = ResourceNode(resource_type=ResourceType.TREE, x=6, y=5, quantity=20, capacity=20)
    world.resources[str(tree.id)] = tree
    resources.reserve(tree.id, actor, 0, 20)
    with pytest.raises(ValueError, match="Chop"):
        resources.gather(tree.id, actor, 20, 0)
    resources.chop(tree.id, actor, 20, 0)
    assert world.inventories[actor].carried == 0
    log = next(node for node in world.resources.values() if node.resource_type == ResourceType.LOG)
    assert log.quantity == 20
    resources.reserve(log.id, actor, 1, 20)
    citizen.x, citizen.y = 1, 1
    with pytest.raises(ValueError, match="beside"):
        resources.gather(log.id, actor, 20, 1)
    citizen.x, citizen.y = 5, 5
    resources.gather(log.id, actor, 20, 2)
    # Depleted nodes are legitimate persisted state, not invalid resource input.
    world = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(world)
    assert world.resources[str(log.id)].quantity == 0
    assert world.inventories[actor].items["wood"] == 20
    store = Structure(structure_type=StructureType.STORAGE, x=5, y=6,
                      builder_id=actor, work_required=1, progress=1)
    world.structures[str(store.id)] = store
    construction = decisions._construction
    construction.transfer_storage(store.id, actor, "wood", 20)
    assert world.inventories[actor].carried == 0
    construction.transfer_storage(store.id, actor, "wood", 20, withdraw=True)
    stone = ResourceNode(resource_type=ResourceType.STONE, x=4, y=5, quantity=5, capacity=5)
    world.resources[str(stone.id)] = stone
    resources.reserve(stone.id, actor, 3, 10)
    resources.gather(stone.id, actor, 5, 3)
    site = construction.start_site(actor, StructureType.SHELTER, 5, 4)
    assert construction.deliver_materials(site.id, actor) == {"wood": 20, "stone": 5}
    construction.apply_work(site.id, actor, site.work_required)
    assert site.completed and world.inventories[actor].carried == 0
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.structures[str(site.id)].completed
    assert restored.model_dump(mode="json") == world.model_dump(mode="json")
