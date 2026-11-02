from app.application.services.hydrology import advance, carve_river
from app.application.services.world_generator import WorldGenerator
from app.application.services.construction_service import ConstructionService
from app.domain.models.calendar import calendar_at_tick, Season, WeatherType
from app.domain.models.structure import StructureType
from app.domain.models.world import World, TerrainType
from tests.test_decisions import _systems


def test_flood_recedes_and_restores_saved_terrain():
    w = WorldGenerator.generate_flat_world(8, 8)
    water = w.retrieve_tile(3, 3)
    water.terrain, water.walkable = TerrainType.WATER, False
    rain = calendar_at_tick(0).model_copy(update={"season": Season.SPRING, "weather": WeatherType.RAIN, "weather_intensity": 1.0})
    for tick in range(20):
        advance(w, tick, rain)
    bank = w.retrieve_tile(3, 4)
    assert not bank.walkable and bank.metadata["flooded"]
    assert bank.terrain == TerrainType.GRASS
    w = World.model_validate_json(w.model_dump_json())
    dry = rain.model_copy(update={"season": Season.SUMMER, "weather": WeatherType.CLEAR})
    for tick in range(20, 55):
        advance(w, tick, dry)
    assert w.retrieve_tile(3, 4).walkable
    assert w.hydrology["flooded_tiles"] == 0


def test_bridge_requires_materials_and_opens_completed_crossing():
    entities, decisions, _ = _systems()
    w = decisions._repository.get()
    tile = w.retrieve_tile(5, 5)
    tile.terrain, tile.walkable = TerrainType.WATER, False
    service = ConstructionService(decisions._repository)
    site = service.start_site("builder", StructureType.BRIDGE, 5, 5)
    assert not tile.walkable and site.missing_materials == {"wood": 16, "stone": 4}
    import pytest
    with pytest.raises(ValueError, match="materials"):
        service.apply_work(site.id, "builder", 28)
    site.materials_delivered = site.materials_required.copy()
    service.apply_work(site.id, "builder", 28)
    assert tile.walkable
    assert not decisions._navigation._structure_blocks(w, 5, 5)
    from app.domain.models.entity import EntityKind
    actor = entities.create(EntityKind.AGENT, "Bridge walker", 4, 5)
    decisions._perception.observe(actor.id, 0)
    energy = actor.needs.energy
    decisions._navigation.plan(actor.id, 5, 5, 1)
    decisions._navigation.advance_all(1)
    assert (actor.x, actor.y) == (5, 5)
    assert actor.metadata["travel_mode"] == "walk"
    assert actor.needs.energy == energy


def test_new_river_deterministic_and_resources_not_in_channel():
    a = WorldGenerator.generate_terrain_world(24, 24, 71)
    b = WorldGenerator.generate_terrain_world(24, 24, 71)
    coords = lambda w: {(t.x, t.y) for c in w.chunks.values() for t in c.tiles.values() if t.metadata.get("river")}
    assert coords(a) == coords(b)
    assert all((r.x, r.y) not in coords(a) for r in a.resources.values())


def test_river_channel_connects_to_water_and_flood_blocks_existing_route():
    w = WorldGenerator.generate_flat_world(8, 8)
    w.retrieve_tile(1, 1).metadata["elevation"] = 1.0
    w.retrieve_tile(6, 6).terrain = TerrainType.WATER
    carve_river(w)
    assert w.retrieve_tile(1, 1).metadata["river"]
    assert w.retrieve_tile(6, 6).metadata["river"]
    entities, decisions, _ = _systems()
    world = decisions._repository.get()
    from app.domain.models.entity import EntityKind
    actor = entities.create(EntityKind.AGENT, "Walker", 4, 5)
    decisions._perception.observe(actor.id, 0)
    plan = decisions._navigation.plan(actor.id, 5, 5, 1)
    world.retrieve_tile(5, 5).walkable = False
    world.retrieve_tile(5, 5).metadata["flooded"] = True
    decisions._navigation.advance_all(1)
    assert (actor.x, actor.y) == (4, 5)
    assert plan.status.value == "BLOCKED"
