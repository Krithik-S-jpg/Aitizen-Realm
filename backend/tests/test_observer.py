from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.application.services.observer_service import snapshot
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.infrastructure.api.v1.observer import local


def analytics():
    return SimpleNamespace(all_events=lambda: [], history=lambda limit: [], _inventory_totals=lambda w: {})


def test_projection_is_read_only_and_redacts_arbitrary_metadata():
    world = WorldGenerator.generate_flat_world(8, 8)
    e = Entity(kind=EntityKind.AGENT, name="Citizen", x=2, y=2, needs=NeedsState(health=20, hunger=90), metadata={"secret": "never_export_me"})
    world.entities[str(e.id)] = e
    before = world.model_dump_json()
    data = snapshot(world, 12, "PAUSED", analytics())
    assert data["population"] == 1 and data["alerts"][0]["severity"] == "DANGER"
    assert "never_export_me" not in str(data)
    assert before == world.model_dump_json()


def test_no_world_and_external_access():
    assert snapshot(None, 0, "STOPPED", analytics())["state"] == "NO_WORLD"
    with pytest.raises(HTTPException):
        local(SimpleNamespace(client=SimpleNamespace(host="192.168.1.5")))
    local(SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")))
