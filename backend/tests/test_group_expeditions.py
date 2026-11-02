from tests.test_community_routines import community
from app.application.services.group_expeditions import advance
from app.domain.models.world import World
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.entity import EntityKind
from app.application.services.entity_service import EntityService


def test_short_party_returns_and_survives_save_load():
    world, a, b, decisions, service = community()
    for e in (a, b):
        world.inventories[str(e.id)].add("food", 3)
        world.inventories[str(e.id)].add("fiber", 1)
    listener = EntityService(decisions._repository).create(EntityKind.AGENT, "Listener", 4, 5)
    discovery = ResourceNode(resource_type=ResourceType.STONE, x=5, y=13, quantity=20, capacity=20)
    world.add_resource(discovery)
    controlled = advance(decisions, world, 6, True)
    assert controlled == {str(a.id), str(b.id)}
    trip = next(iter(world.expeditions.values()))
    assert trip["phase"] == "preparing"
    restored = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    for tick in range(7, 46):
        decisions._navigation.advance_all(tick)
        advance(decisions, restored, tick, tick < 18)
        if restored.expeditions[trip["id"]]["phase"] in {"completed", "aborted"}:
            break
    result = restored.expeditions[trip["id"]]
    assert result["phase"] == "completed", result
    assert result["reports"]
    learned = restored.entity_knowledge[str(listener.id)].resources[str(discovery.id)]
    assert learned.source_entity_id in {a.id, b.id}
    assert learned.confidence == .75
    for key in result["members"]:
        actor = restored.entities[key]
        assert [actor.x, actor.y] == result["origins"][key]
        assert "group_expedition" not in actor.metadata


def test_no_free_supplies_or_unprepared_trip():
    world, a, b, decisions, service = community()
    assert not advance(decisions, world, 6, True)
    assert not world.expeditions
    assert not world.inventories[str(a.id)].items


def test_companion_first_aid_consumes_fiber_once_and_returns():
    world, a, b, decisions, service = community()
    b.x = 6
    for e in (a, b):
        world.inventories[str(e.id)].add("food", 3)
    world.inventories[str(b.id)].add("fiber", 2)
    advance(decisions, world, 6, True)
    assert world.expeditions
    a.needs.health = 65
    advance(decisions, world, 7, True)
    assert a.needs.health == 70
    assert world.inventories[str(b.id)].items["fiber"] == 1
    advance(decisions, world, 8, True)
    assert world.inventories[str(b.id)].items["fiber"] == 1


def supplied_party():
    world, a, b, decisions, _ = community()
    for e in (a, b):
        world.inventories[str(e.id)].add("food", 3)
        world.inventories[str(e.id)].add("fiber", 1)
    return world, a, b, decisions


def test_equipment_is_gathered_before_departure():
    world, a, b, decisions = supplied_party()
    world.inventories[str(a.id)].consume({"fiber": 1})
    reeds = ResourceNode(resource_type=ResourceType.REEDS, x=5, y=6, quantity=10, capacity=10)
    world.add_resource(reeds)
    decisions._perception.observe(a.id, 5)
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    for tick in range(7, 25):
        decisions._navigation.advance_all(tick)
        advance(decisions, world, tick, True)
        if trip["phase"] != "preparing":
            break
    assert trip["phase"] == "outbound", trip
    assert world.inventories[str(a.id)].items.get("fiber", 0) >= 1
    assert reeds.quantity < 10


def test_cave_party_roundtrip():
    from app.application.services.cave_service import CaveService
    world, a, b, decisions = supplied_party()
    world.caves_initialized = True
    world.caves = {"test": dict(id="test", x=6, y=5, floor=[[0, 0], [1, 0], [2, 0]])}
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    assert trip["kind"] == "cave"
    seen_inside = False
    for tick in range(7, 45):
        decisions._navigation.advance_all(tick)
        CaveService(decisions._repository).advance_all(tick)
        advance(decisions, world, tick, True)
        seen_inside |= all(e.metadata.get("in_cave") for e in (a, b))
        if trip["phase"] in {"completed", "aborted"}:
            break
    assert seen_inside
    assert trip["phase"] == "completed", trip
    assert all("test" in e.metadata["explored_caves"] for e in (a, b))


def test_casualty_pickup_is_physical_and_persists():
    world, a, b, decisions = supplied_party()
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    a.needs.health = 20
    a.x, a.y = 5, 7
    advance(decisions, world, 7, True)
    assert (a.x, a.y) == (5, 7)
    assert not trip["rescue"]["picked_up"]
    restored = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    for tick in range(8, 40):
        decisions._navigation.advance_all(tick)
        advance(decisions, restored, tick, True)
        if restored.expeditions[trip["id"]]["phase"] == "rescued":
            break
    result = restored.expeditions[trip["id"]]
    assert result["phase"] == "rescued", result
    patient = restored.entities[str(a.id)]
    assert [patient.x, patient.y] == result["origins"][str(b.id)]
    assert patient.needs.health == 20
    assert "carried_by" not in patient.metadata


def test_two_boat_party_returns():
    from app.domain.models.world import TerrainType
    world, a, b, decisions = supplied_party()
    for y in range(16):
        tile = world.retrieve_tile(8, y)
        tile.terrain, tile.walkable = TerrainType.WATER, False
    for e in (a, b):
        world.inventories[str(e.id)].add("boat", 1)
        decisions._perception.observe(e.id, 5)
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    assert trip["kind"] == "boat"
    for tick in range(7, 85):
        decisions._navigation.advance_all(tick)
        advance(decisions, world, tick, True)
        if trip["phase"] in {"completed", "aborted"}:
            break
    assert trip["phase"] == "completed", trip
    assert len(trip["boat_started"]) == 2
    assert all(not e.metadata.get("aboard") for e in (a, b))


def test_planner_rejects_old_world_and_falls_back():
    from concurrent.futures import Future
    from app.application.services.expedition_planner import ExpeditionPlanner
    planner = ExpeditionPlanner()
    world = object()
    trip = dict(id="trip", started_tick=0, options=[{"kind": "survey"}])
    planner.pending = Future()
    planner.pending.set_result({"choice": 0, "reason": "Old world"})
    planner.context = (object(), "trip", 0)
    assert planner.choose(world, trip, 8, "test")[2] == "utility_fallback"
    planner.pool.shutdown()


def test_planner_accepts_only_offered_itinerary():
    from concurrent.futures import Future
    from app.application.services.expedition_planner import ExpeditionPlanner
    planner = ExpeditionPlanner()
    world = object()
    trip = dict(id="trip", started_tick=0, options=[{"kind": "survey"}, {"kind": "cave"}])
    for chosen, expected in ((1, "local_llm"), (99, "utility_fallback")):
        planner.pending = Future()
        planner.pending.set_result({"choice": chosen, "reason": "Explore the known entrance"})
        planner.context = (world, "trip", 0)
        assert planner.choose(world, trip, 1, "test")[2] == expected
    planner.pool.shutdown()


def test_missing_equipment_aborts_without_creating_it():
    world, a, b, decisions, _ = community()
    for e in (a, b):
        world.inventories[str(e.id)].add("food", 3)
    advance(decisions, world, 6, True)
    advance(decisions, world, 7, True)
    trip = next(iter(world.expeditions.values()))
    assert trip["phase"] == "aborted"
    assert "No known source" in trip["reason"]
    assert all(not world.inventories[str(e.id)].items.get("fiber") for e in (a, b))
    assert not world.active_actions
