import pytest
from app.application.services import editor_tools as tools, world_editor
from app.application.services.world_generator import WorldGenerator
from app.domain.models.world import World
from app.domain.models.calendar import calendar_at_tick


def paint(world, tool, choice, radius=0):
    preview = tools.preview(world, 3, 3, radius, tool, choice, 0)
    assert "terrain" not in preview
    return tools.apply(world, 3, 3, radius, tool, choice, 0, preview["token"])


@pytest.mark.parametrize("choice", sorted(tools.RESOURCES))
def test_resource_brush_saved_undo_and_occupancy(choice):
    world = WorldGenerator.generate_flat_world(8, 8)
    paint(world, "resource", choice, 1)
    assert len(world.resources) == 5
    assert all(node.quantity == 30 for node in world.resources.values())
    assert not tools.preview(world, 3, 3, 1, "resource", choice, 0)["can_apply"]
    restored = World.model_validate_json(world.model_dump_json())
    world_editor.undo(restored, 0)
    assert not restored.resources


def test_weather_overlap_expiry_and_persistence():
    world = WorldGenerator.generate_flat_world(8, 8)
    calendar = calendar_at_tick(0)
    paint(world, "weather", "RAIN", 2)
    paint(world, "weather", "CLEAR")
    world = World.model_validate_json(world.model_dump_json())
    assert tools.local_weather(world, 3, 3, calendar, 0).weather.value == "CLEAR"
    assert tools.local_weather(world, 4, 3, calendar, 0).weather.value == "RAIN"
    assert tools.local_weather(world, 0, 0, calendar, 0) is calendar
    assert tools.local_weather(world, 4, 3, calendar, 48) is calendar
    world_editor.undo(world, 0)
    assert tools.local_weather(world, 3, 3, calendar, 0).weather.value == "RAIN"


@pytest.mark.parametrize("choice", sorted(tools.SCENARIOS))
def test_scenario_presets(choice):
    world = WorldGenerator.generate_flat_world(8, 8)
    paint(world, "scenario", choice)
    assert world.resources or world.weather_patches
    world_editor.undo(world, 0)
    assert not world.resources and not world.weather_patches


def test_bounds_and_weather_limit():
    world = WorldGenerator.generate_flat_world(8, 8)
    assert not tools.preview(world, 0, 0, 2, "weather", "RAIN", 0)["can_apply"]
    for _ in range(4):
        paint(world, "weather", "RAIN")
    assert not tools.preview(world, 3, 3, 0, "weather", "RAIN", 0)["can_apply"]


def test_painted_rain_only_floods_local_banks():
    from app.application.services.hydrology import advance
    from app.domain.models.world import TerrainType
    from app.domain.models.calendar import WeatherType
    world = WorldGenerator.generate_flat_world(8, 8)
    for x, y in [(3, 2), (6, 6)]:
        tile = world.retrieve_tile(x, y)
        tile.terrain, tile.walkable = TerrainType.WATER, False
    paint(world, "weather", "RAIN")
    calendar = calendar_at_tick(0).model_copy(update={"weather": WeatherType.CLEAR, "weather_intensity": 0.0})
    for tick in range(20):
        advance(world, tick, calendar)
    assert world.retrieve_tile(3, 3).metadata["flooded"]
    assert not world.retrieve_tile(6, 5).metadata["flooded"]
