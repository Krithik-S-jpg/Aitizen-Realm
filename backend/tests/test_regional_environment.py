from types import SimpleNamespace
from app.application.services.regional_environment import advance, climate, growth_factor
from app.application.services.world_generator import WorldGenerator
from app.domain.models.calendar import CalendarControl, configure_calendar_control, reset_calendar_control
from app.domain.models.world import World


def weather(kind="RAIN", temperature=20):
    return SimpleNamespace(weather=SimpleNamespace(value=kind), temperature_c=temperature, weather_intensity=1)


def test_rain_and_drought_change_soil_without_changing_terrain():
    configure_calendar_control(0, CalendarControl(ticks_per_day=120))
    try:
        world = WorldGenerator.generate_flat_world(16,16)
        tile = world.retrieve_tile(8,8)
        terrain = tile.terrain
        advance(world,12,weather())
        wet = tile.metadata["soil_moisture"]
        advance(world,12,weather())
        assert tile.metadata["soil_moisture"] == wet
        advance(world,24,weather("CLEAR",40))
        assert tile.metadata["soil_moisture"] < wet
        assert tile.terrain == terrain
        restored = World.model_validate_json(world.model_dump_json())
        assert restored.ecology == world.ecology
        assert restored.retrieve_tile(8,8).metadata == tile.metadata
    finally:
        reset_calendar_control()


def test_chunk_budget_and_highland_cooling():
    world = WorldGenerator.generate_flat_world(32,32)
    advance(world,12,weather())
    updated = [t for c in world.chunks.values() for t in c.tiles.values() if "soil_tick" in t.metadata]
    assert len(updated) <= 256
    tile = world.retrieve_tile(8,8)
    tile.metadata["elevation"] = .3
    low = climate(world,tile)["temperature_offset_c"]
    tile.metadata["elevation"] = .9
    assert climate(world,tile)["temperature_offset_c"] < low
    tile.metadata.update(soil_moisture=.01, snow_cover=0)
    dry = growth_factor(tile)
    tile.metadata["soil_moisture"] = .6
    assert growth_factor(tile) > dry


def test_snow_accumulates_and_abandoned_traffic_decays():
    configure_calendar_control(0, CalendarControl(ticks_per_day=12))
    try:
        world = WorldGenerator.generate_flat_world(16,16)
        tile = world.retrieve_tile(8,8)
        tile.metadata.update(foot_traffic=10, last_traffic_tick=0)
        advance(world,12,weather("SNOW",-5))
        assert tile.metadata["snow_cover"] > 0
        assert tile.metadata["foot_traffic"] == 9
    finally:
        reset_calendar_control()
