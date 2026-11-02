from app.application.services.flood_response import evacuate, propose_bridge, warn_neighbors
from app.domain.models.world import TerrainType, World
from app.domain.models.structure import StructureType
from tests.test_community_routines import community


def test_evacuation_walks_and_warning_is_local_persistent_and_deduplicated():
    world, actor, listener, decisions, chat = community()
    actor.metadata["state"] = "sleep"
    for x in (4, 5, 6):
        for y in (4, 5, 6):
            tile = world.retrieve_tile(x, y)
            tile.metadata["flooded"], tile.walkable = True, False
    assert evacuate(decisions, world, actor, 1)
    assert (actor.x, actor.y) == (5, 5)
    warn_neighbors(chat, world, 1)
    warn_neighbors(chat, world, 2)
    assert len(world.messages) == 1
    assert listener.metadata["flood_warning"]["experience"] == "heard"
    restored = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    actor = restored.entities[str(actor.id)]
    for tick in range(2, 8):
        old = (actor.x, actor.y)
        decisions._navigation.advance_all(tick)
        assert abs(actor.x-old[0]) + abs(actor.y-old[1]) <= 1
        if not evacuate(decisions, restored, actor, tick):
            break
    assert not restored.retrieve_tile(actor.x, actor.y).metadata.get("flooded")
    assert not actor.metadata.get("flood_evacuating")


def test_trapped_citizen_does_not_teleport():
    world, actor, _, decisions, _ = community()
    for chunk in world.chunks.values():
        for tile in chunk.tiles.values():
            tile.walkable = False
            tile.metadata["flooded"] = True
    assert evacuate(decisions, world, actor, 1)
    assert str(actor.id) not in world.movement_plans
    assert (actor.x, actor.y) == (5, 5)


def test_useful_bridge_proposal_enters_existing_job_board_without_free_goods():
    world, actor, _, decisions, _ = community()
    for y in range(world.height):
        tile = world.retrieve_tile(6, y)
        tile.terrain, tile.walkable = TerrainType.WATER, False
    decisions._perception.observe(actor.id, 1)
    propose_bridge(decisions, world, actor, 1)
    bridges = [s for s in world.structures.values() if s.structure_type == StructureType.BRIDGE]
    assert len(bridges) == 1
    assert not bridges[0].funded and not bridges[0].completed
    propose_bridge(decisions, world, actor, 25)
    assert len(world.structures) == 1
    from app.application.services.settlement_service import SettlementService
    SettlementService(decisions._repository).advance_all(25)
    assert any(job.target_id == str(bridges[0].id) for job in world.settlement_jobs.values())
    pack = world.inventories[str(actor.id)]
    pack.add("wood", 16)
    pack.add("stone", 4)
    # Exercise the normal autonomous decision/build loop, not direct apply_work.
    for tick in range(26, 145):
        decisions._navigation.advance_all(tick)
        decisions.advance_all(tick)
        if bridges[0].completed:
            break
    assert bridges[0].completed
    assert bridges[0].materials_delivered == {"wood": 16, "stone": 4}
    assert world.retrieve_tile(6, 5).walkable


def test_no_bridge_for_short_detour_or_unknown_opposite_bank():
    world, actor, _, decisions, _ = community()
    tile = world.retrieve_tile(6, 5)
    tile.terrain, tile.walkable = TerrainType.WATER, False
    decisions._perception.observe(actor.id, 1)
    propose_bridge(decisions, world, actor, 1)
    assert not world.structures
    world.entity_knowledge[str(actor.id)].tiles.pop("7,5", None)
    propose_bridge(decisions, world, actor, 25)
    assert not world.structures
