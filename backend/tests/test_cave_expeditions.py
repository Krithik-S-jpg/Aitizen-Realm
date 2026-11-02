from app.application.services.cave_service import CaveService
from app.application.services.expedition_service import consider_expedition, advance_auto_voyage
from app.domain.models.world import World
from app.domain.models.calendar import calendar_at_tick, DayPhase
from tests.test_water_travel import crossing


def daytime():
    return next(t for t in range(100) if calendar_at_tick(t).phase == DayPhase.DAY)


def test_chamber_upgrade_preserves_saved_passages_and_connectivity():
    cave = dict(id="legacy", x=3, y=5, floor=[[0, 0], [1, 0], [2, 0]])
    CaveService._expand_chambers(cave, 42)
    floor = {tuple(p) for p in cave["floor"]}
    assert {(0, 0), (1, 0), (2, 0)} <= floor
    assert len(floor) > 70
    visited = {(0, 0)}
    queue = [(0, 0)]
    while queue:
        x, y = queue.pop()
        for p in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
            if p in floor and p not in visited:
                visited.add(p)
                queue.append(p)
    assert visited == floor
    CaveService._expand_chambers(cave, 42)
    assert floor == {tuple(p) for p in cave["floor"]}


def test_autonomous_dive_and_survival_priority():
    world, citizen, nav, decisions = crossing()
    citizen.needs.health = 15
    assert not consider_expedition(decisions, world, citizen, daytime(), [])
    citizen.needs.health = 100
    assert consider_expedition(decisions, world, citizen, daytime(), [])
    assert citizen.metadata.get("dive_trip")


def test_cave_roundtrip_and_save_midway():
    world, citizen, nav, decisions = crossing()
    cave = dict(id="test", x=3, y=5, floor=[[0, 0], [1, 0], [2, 0], [2, 1]])
    world.caves = {"test": cave}
    world.caves_initialized = True
    service = CaveService(decisions._repository)
    service.enter(citizen.id, 1)
    service.advance_all(2)
    assert citizen.metadata["cave_position"] == [1, 0]
    restored = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    citizen = restored.entities[str(citizen.id)]
    for tick in range(3, 12):
        service.advance_all(tick)
        assert citizen.metadata["cave_position"] in cave["floor"]
    assert not citizen.metadata["in_cave"]
    assert citizen.metadata["cave_position"] == [0, 0]
    assert citizen.metadata["explored_caves"] == ["test"]


def test_autonomous_boat_crafting_consumes_actual_materials():
    world, citizen, nav, decisions = crossing()
    citizen.metadata["underwater_explored"] = ["4,5"]
    inventory = decisions._resources.inventory_for(str(citizen.id))
    inventory.add("wood", 20)
    inventory.add("fiber", 8)
    assert consider_expedition(decisions, world, citizen, daytime(), [])
    assert inventory.items.get("boat") == 1
    assert inventory.items.get("wood", 0) == 0
    assert inventory.items.get("fiber", 0) == 0


def test_autonomous_voyage_returns_to_shore():
    world, citizen, nav, decisions = crossing()
    inventory = decisions._resources.inventory_for(str(citizen.id))
    inventory.add("boat", 1)
    tick = daytime()
    assert consider_expedition(decisions, world, citizen, tick, [])
    assert consider_expedition(decisions, world, citizen, tick + 1, [])
    assert citizen.metadata.get("aboard")
    for now in range(tick + 2, tick + 25):
        nav.advance_all(now)
        advance_auto_voyage(decisions, world, citizen, now)
    assert not citizen.metadata.get("aboard")
    assert not citizen.metadata.get("auto_voyage")
    assert world.retrieve_tile(citizen.x, citizen.y).walkable


def test_isolated_pond_voyage_anchors_before_return_operations():
    world, citizen, nav, decisions = crossing(width=1)
    from app.domain.models.world import TerrainType
    for y in range(16):
        if y != 5:
            tile = world.retrieve_tile(4, y)
            tile.terrain = TerrainType.GRASS
            tile.walkable = True
    decisions._perception.observe(citizen.id, 0)
    decisions._resources.inventory_for(str(citizen.id)).add("boat", 1)
    tick = daytime()
    assert consider_expedition(decisions, world, citizen, tick, [])
    assert consider_expedition(decisions, world, citizen, tick + 1, [])
    for now in range(tick + 2, tick + 15):
        nav.advance_all(now)
        advance_auto_voyage(decisions, world, citizen, now)
    assert not citizen.metadata.get("aboard")
    assert world.retrieve_tile(citizen.x, citizen.y).walkable
