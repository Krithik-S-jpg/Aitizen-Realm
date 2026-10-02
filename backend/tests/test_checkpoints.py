"""Checkpoint authorization and snapshot capture tests without hosted writes."""

from uuid import uuid4

import httpx

from fastapi.testclient import TestClient

from app.domain.models.calendar import get_calendar_control
from app.infrastructure.api.dependencies import get_engine_service, get_world_service
from app.infrastructure.api.v1.checkpoints import checkpoint_store
from app.main import app


def test_checkpoint_routes_deny_unconfigured_access() -> None:
    """No default token means fail closed, not anonymous database access."""
    with TestClient(app) as client:
        assert client.get("/api/v1/checkpoints").status_code == 401
        assert client.get("/api/v1/checkpoints/status").status_code == 401


def test_connection_status_verifies_read_and_sanitizes_failure() -> None:
    class Store:
        broken = False

        async def read(self):
            if self.broken:
                raise httpx.ConnectError("private credential diagnostic")
            return []

    store = Store()
    app.dependency_overrides[checkpoint_store] = lambda: store
    try:
        with TestClient(app) as client:
            result = client.get("/api/v1/checkpoints/status")
            assert result.status_code == 200
            assert result.json()["connected"] is True
            store.broken = True
            result = client.get("/api/v1/checkpoints/status")
            assert result.status_code == 502
            assert "private" not in result.text
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)


def test_checkpoint_capture_uses_real_world() -> None:
    """The backup contains domain state and calendar, not fabricated metrics."""
    saved = []

    class Store:
        async def save(self, record: dict) -> dict:
            saved.append(record)
            return record

    app.dependency_overrides[checkpoint_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            client.get("/api/v1/world")
            result = client.post("/api/v1/checkpoints", json={"label": "Test"})
            assert result.status_code == 201, result.text
            assert "payload" not in result.json()
            assert saved[0]["payload"]["world"]["chunks"]
            assert saved[0]["payload"]["calendar"]["ticks_per_day"] >= 12
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)


def test_complete_save_captures_matching_archive_and_world():
    received = []

    class Store:
        async def save_complete(self, record, archive):
            received.append((record, archive))
            return {"id": record["id"], "archive_saved": True}

    app.dependency_overrides[checkpoint_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            client.get("/api/v1/world")
            response = client.post("/api/v1/checkpoints",
                                   json={"label": "Complete", "include_archive": True})
            assert response.status_code == 201, response.text
            assert response.json()["archive_saved"]
            record, archive = received[0]
            assert record["tick"] == archive["current_tick"]
            assert "episodes" in record["payload"]["world"]
            assert all(key in archive for key in ("events", "metrics", "experiments"))
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)


def test_overwrite_uses_selected_id_and_rejects_missing_slot():
    selected = uuid4()
    captured = []

    class Store:
        missing = False

        async def overwrite(self, record, archive):
            if self.missing:
                raise LookupError()
            captured.append((record, archive))
            return {"id": record["id"], "overwritten": True}

    store = Store()
    app.dependency_overrides[checkpoint_store] = lambda: store
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            client.get("/api/v1/world")
            for complete in (False, True):
                response = client.post("/api/v1/checkpoints", json={
                    "overwrite_id": str(selected), "include_archive": complete})
                assert response.status_code == 201
                assert response.json()["overwritten"]
                assert captured[-1][0]["id"] == str(selected)
                assert (captured[-1][1] is not None) == complete
            store.missing = True
            assert client.post("/api/v1/checkpoints", json={
                "overwrite_id": str(selected)}).status_code == 404
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)


def test_restore_round_trip_and_reject_invalid_payload() -> None:
    """Restore real world state and clock; invalid data must leave it intact."""
    checkpoint_id = uuid4()
    record = {}

    class Store:
        async def read(self, requested_id):
            assert requested_id == checkpoint_id
            return [record]

    app.dependency_overrides[checkpoint_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            client.get("/api/v1/world")
            world = get_world_service().get_world()
            assert world is not None
            record.update(
                {
                    "schema_version": 1,
                    "tick": 37,
                    "payload": {
                        "world": world.model_dump(mode="json"),
                        "calendar": get_calendar_control().model_dump(mode="json"),
                        "tick_rate": 2.0,
                    },
                }
            )
            expected = world.model_dump(mode="json")
            world.entities.clear()
            response = client.post(f"/api/v1/checkpoints/{checkpoint_id}/restore")
            assert response.status_code == 200, response.text
            assert get_world_service().get_world().model_dump(mode="json") == expected
            assert get_engine_service().get_current_tick().value == 37
            assert get_engine_service().get_tick_rate() == 2.0
            record["payload"]["tick_rate"] = -1
            response = client.post(f"/api/v1/checkpoints/{checkpoint_id}/restore")
            assert response.status_code == 422
            assert get_engine_service().get_current_tick().value == 37
            client.post("/api/v1/simulation/step")
            assert get_engine_service().get_current_tick().value == 38
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)
