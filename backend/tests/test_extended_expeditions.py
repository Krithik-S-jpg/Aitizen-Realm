from app.application.services.group_expeditions import advance
from app.application.services.cave_service import CaveService
from app.domain.models.world import World, TerrainType
from tests.test_group_expeditions import supplied_party


def test_two_day_camp_rest_and_return_survive_reload():
    world, a, b, decisions = supplied_party()
    water = world.retrieve_tile(6, 8)
    water.terrain, water.walkable = TerrainType.WATER, False
    for e in (a, b):
        world.inventories[str(e.id)].add("food", 8)
        decisions._perception.observe(e.id, 5)
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    assert trip["kind"] == "multi_day"
    rested = False
    for tick in range(7, 75):
        decisions._navigation.advance_all(tick)
        decisions._needs.advance_all(tick)
        advance(decisions, world, tick, 6 <= tick % 24 < 20)
        if tick == 21:
            assert trip["phase"] == "camping"
            world = World.model_validate_json(world.model_dump_json())
            decisions._repository.save(world)
            trip = world.expeditions[trip["id"]]
            rested = True
        if trip["phase"] in {"completed", "aborted"}:
            break
    assert rested and trip["overnight_complete"]
    assert trip["phase"] == "completed", trip
    assert trip["finished_tick"] - trip["started_tick"] >= 24


def test_cave_casualty_extraction_and_land_delivery():
    world, a, b, decisions = supplied_party()
    world.caves_initialized = True
    world.caves = {"test": dict(id="test", x=6, y=5, floor=[[0, 0], [1, 0], [2, 0]])}
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    for e in (a, b):
        e.x, e.y = 6, 5
        CaveService(decisions._repository).enter(e.id, 7)
    a.metadata["cave_position"] = [2, 0]
    b.metadata["cave_position"] = [1, 0]
    a.needs.health = 20
    for tick in range(8, 25):
        advance(decisions, world, tick, True)
        CaveService(decisions._repository).advance_all(tick)
        decisions._navigation.advance_all(tick)
        if trip["phase"] == "rescued":
            break
    assert trip["phase"] == "rescued", trip
    assert trip["rescue"]["extracted_tick"]
    assert not a.metadata.get("in_cave")
    assert [a.x, a.y] == trip["origins"][str(b.id)]


def test_underwater_tow_returns_to_shore_without_teleport():
    world, a, b, decisions = supplied_party()
    advance(decisions, world, 6, True)
    trip = next(iter(world.expeditions.values()))
    for x in (5, 6):
        tile = world.retrieve_tile(x, 6)
        tile.terrain, tile.walkable = TerrainType.WATER, False
    for e, x in ((a, 6), (b, 5)):
        e.x, e.y = x, 6
        e.metadata.update(dive_trip=True, underwater=True, dive_origin=[5, 5], oxygen=100)
        decisions._perception.observe(e.id, 7)
    a.needs.health = 20
    previous = a.x, a.y
    for tick in range(8, 25):
        advance(decisions, world, tick, True)
        assert abs(a.x-previous[0])+abs(a.y-previous[1]) <= 1
        previous = a.x, a.y
        if tick == 8:
            world = World.model_validate_json(world.model_dump_json())
            decisions._repository.save(world)
            a, b = world.entities[str(a.id)], world.entities[str(b.id)]
            trip = world.expeditions[trip["id"]]
        decisions._navigation.advance_all(tick)
        if trip["phase"] == "rescued":
            break
    assert trip["phase"] == "rescued", trip
    assert not a.metadata["underwater"]
    assert a.metadata["oxygen"] == 100


def test_underwater_rescue_refuses_insufficient_return_reserve():
    from app.application.services.interior_rescue import start
    world, a, b, decisions = supplied_party()
    for e in (a, b):
        e.metadata.update(dive_trip=True, underwater=True, oxygen=10)
    assert start(world, a, b) is None
