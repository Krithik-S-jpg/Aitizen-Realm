import pytest
from app.application.services import world_editor as editor
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.world import World


def test_atomic_brush_preview_apply_and_persisted_undo():
    world = WorldGenerator.generate_flat_world(8, 8)
    original = world.retrieve_tile(3, 3).model_dump()
    preview = editor.preview(world, 3, 3, 1, "WATER", 0)
    assert preview["can_apply"] and len(preview["tiles"]) == 5
    assert world.retrieve_tile(3, 3).walkable
    editor.apply(world, 3, 3, 1, "WATER", 0, preview["token"])
    assert not world.retrieve_tile(3, 3).walkable
    restored = World.model_validate_json(world.model_dump_json())
    editor.undo(restored, 0)
    assert restored.retrieve_tile(3, 3).model_dump() == original


def test_occupied_brush_is_rejected_without_partial_edit():
    world = WorldGenerator.generate_flat_world(8, 8)
    citizen = Entity(kind=EntityKind.AGENT, name="Citizen", x=4, y=3)
    world.entities[str(citizen.id)] = citizen
    preview = editor.preview(world, 3, 3, 1, "WATER", 0)
    assert not preview["can_apply"]
    with pytest.raises(ValueError):
        editor.apply(world, 3, 3, 1, "WATER", 0, preview["token"])
    assert world.retrieve_tile(3, 3).walkable
    assert not world.editor_history


def test_stale_preview_and_advanced_undo_rejected():
    world = WorldGenerator.generate_flat_world(8, 8)
    preview = editor.preview(world, 3, 3, 0, "WATER", 0)
    with pytest.raises(ValueError):
        editor.apply(world, 3, 3, 0, "WATER", 1, preview["token"])
    editor.apply(world, 3, 3, 0, "WATER", 0, preview["token"])
    with pytest.raises(ValueError):
        editor.undo(world, 1)
    assert not world.retrieve_tile(3, 3).walkable


def test_api_refuses_running_and_inflight_ticks(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.infrastructure.api import dependencies
    from app.infrastructure.api.v1.world import edit_terrain, TerrainBrush
    from app.domain.models.engine import EngineState
    engine = SimpleNamespace(_stepping=False, get_state=lambda: EngineState.RUNNING)
    monkeypatch.setattr(dependencies, "_engine", engine)
    brush = TerrainBrush(x=3, y=3, terrain="WATER")
    for operation in ("preview", "apply", "undo"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(edit_terrain(operation, brush, None))
        assert error.value.status_code == 409
    engine.get_state = lambda: EngineState.PAUSED
    engine._stepping = True
    with pytest.raises(HTTPException):
        asyncio.run(edit_terrain("apply", brush, None))


def test_bank_cache_rebuild_does_not_turn_painted_water_walkable():
    from app.application.services.hydrology import advance
    from app.domain.models.calendar import calendar_at_tick
    from app.domain.models.world import TerrainType
    world = WorldGenerator.generate_flat_world(8, 8)
    world.retrieve_tile(3, 3).terrain = TerrainType.WATER
    world.retrieve_tile(3, 3).walkable = False
    advance(world, 0, calendar_at_tick(0))
    preview = editor.preview(world, 3, 4, 0, "WATER", 0)
    editor.apply(world, 3, 4, 0, "WATER", 0, preview["token"])
    advance(world, 1, calendar_at_tick(1))
    assert not world.retrieve_tile(3, 4).walkable
