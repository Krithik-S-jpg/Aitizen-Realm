"""Physical layout and interior exploration regression scenarios."""
import pytest
from app.application.services.construction_service import ConstructionService
from app.application.services.cave_service import CaveService
from app.application.services.marine_service import MarineService
from app.domain.models.structure import StructureType
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import World
from tests.test_water_travel import crossing


def test_foundation_blocks_routes_but_preserves_door_and_saved_footprint():
    world, citizen, nav, decisions = crossing()
    site = decisions._construction.start_site(str(citizen.id), StructureType.SHELTER, 9, 9)
    assert len(site.footprint) == 4
    assert all(nav._structure_blocks(world, *p) for p in site.footprint)
    assert not nav._structure_blocks(world, *site.entrance)
    citizen.x, citizen.y = 7, 9
    decisions._perception.observe(citizen.id, 1)
    route = nav.plan(citizen.id, 11, 9, 1)
    assert not set(route.path) & site.footprint
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.structures[str(site.id)].footprint == site.footprint
    with pytest.raises(ValueError):
        decisions._construction.start_site(str(citizen.id), StructureType.TENT, 10, 9)
    site.progress = site.work_required
    site.resident_ids.append(str(citizen.id))
    citizen.metadata["assigned_home_id"] = str(site.id)
    decisions._perception.observe(citizen.id, 1)
    target = decisions._safe_target(world, citizen)
    assert (target["x"], target["y"]) == site.entrance


def test_foundation_rejects_tree_and_does_not_consume_materials():
    world, citizen, nav, decisions = crossing()
    tree = ResourceNode(resource_type=ResourceType.TREE, x=8, y=8, quantity=10, capacity=10)
    world.resources[str(tree.id)] = tree
    with pytest.raises(ValueError, match="Clear trees"):
        ConstructionService.validate_space(world, StructureType.SHELTER, 9, 9)
    assert not world.structures


def test_cave_ore_is_finite_and_maps_survive_reload():
    world, citizen, nav, decisions = crossing()
    cave = dict(id="mine", x=3, y=5, floor=[[0,0],[1,0],[2,0]], layout_version=2,
                features_version=1, features={"1,0":{"kind":"ore","remaining":2}}, surveyed=[[0,0]])
    world.caves={"mine":cave}
    world.caves_initialized=True
    inventory=world.inventories[str(citizen.id)]
    inventory.add("stone_pickaxe",1)
    service=CaveService(decisions._repository)
    service.enter(citizen.id,0)
    service.advance_all(1)
    assert inventory.items["ore"] == 1
    assert cave["features"]["1,0"]["remaining"] == 1
    service.advance_all(1)
    assert inventory.items["ore"] == 1
    restored=World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    for tick in range(2,8):
        service.advance_all(tick)
    actor=restored.entities[str(citizen.id)]
    assert not actor.metadata["in_cave"]
    assert actor.metadata["cave_maps"]["mine"]
    assert restored.caves["mine"]["features"]["1,0"]["remaining"] == 0


def test_dive_conditions_require_equipment_and_reject_poor_visibility():
    world, citizen, nav, decisions = crossing()
    tile=world.retrieve_tile(4,5)
    tile.metadata["marine"]={"depth":12,"temperature_c":10,"current":.6,"visibility":.8}
    assert not MarineService.safe_dive(world,citizen,tile)
    world.inventories[str(citizen.id)].add("diving_gear",1)
    assert MarineService.safe_dive(world,citizen,tile)
    tile.metadata["marine"]["visibility"]=.1
    assert not MarineService.safe_dive(world,citizen,tile)


def test_shared_cave_routes_keep_provenance_and_do_not_become_personal_exploration():
    from app.application.services.communication_service import CommunicationService
    from app.application.services.memory_service import MemoryService
    from app.domain.models.entity import EntityKind
    world, citizen, nav, decisions = crossing()
    from app.application.services.entity_service import EntityService
    listener=EntityService(decisions._repository).create(EntityKind.AGENT,"Listener",3,6)
    citizen.metadata["cave_maps"]={"cave-a":[[0,0],[1,0]]}
    service=CommunicationService(decisions._repository,MemoryService(decisions._repository))
    message=service.send(citizen.id,listener.id,"I marked the cave return route.",1,{"cave_routes":["cave-a","invented"]})
    assert message.transferred_count == 1
    report=listener.metadata["reported_cave_routes"]["cave-a"]
    assert report["source_id"] == str(citizen.id)
    assert "cave_maps" not in listener.metadata
    citizen.metadata["cave_maps"]["cave-a"].append([2,0])
    assert len(report["route"]) == 2
