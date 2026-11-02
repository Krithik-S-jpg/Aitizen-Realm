import gzip
import json

import pytest

from app.domain.models.calendar import CalendarControl
from app.infrastructure.repositories.local_recovery import LocalRecovery, RecoveryState
from tests.test_decisions import _systems


def snapshot(tick):
    _, decisions, _ = _systems()
    return RecoveryState(tick=tick, tick_rate=1, calendar=CalendarControl(), world=decisions._require_world())


def test_roundtrip_and_overwrite(tmp_path):
    store = LocalRecovery(tmp_path / "world.gz")
    assert store.read() is None
    store.write_payload(snapshot(10).model_dump_json())
    store.write_payload(snapshot(20).model_dump_json())
    assert store.read().tick == 20
    assert store.decode(store.previous.read_bytes()).tick == 10


def test_corruption_recovers_previous_and_preserves_it(tmp_path):
    store = LocalRecovery(tmp_path / "world.gz")
    store.write_payload(snapshot(10).model_dump_json())
    store.write_payload(snapshot(20).model_dump_json())
    store.path.write_bytes(b"broken")
    assert store.read().tick == 10
    store.write_payload(snapshot(30).model_dump_json())
    assert store.decode(store.previous.read_bytes()).tick == 10


def test_checksum_and_schema_rejected(tmp_path):
    store = LocalRecovery(tmp_path / "world.gz")
    store.path.write_bytes(gzip.compress(json.dumps({"payload": "{}", "sha256": "wrong"}).encode()))
    with pytest.raises(ValueError, match="No valid"):
        store.read()
    state = snapshot(10).model_dump()
    state["version"] = 999
    with pytest.raises(ValueError):
        RecoveryState.model_validate(state)


def test_failed_replace_keeps_last_generation(tmp_path, monkeypatch):
    store = LocalRecovery(tmp_path / "world.gz")
    store.write_payload(snapshot(10).model_dump_json())
    def fail(*_):
        raise OSError("disk unavailable")
    monkeypatch.setattr("app.infrastructure.repositories.local_recovery.os.replace", fail)
    with pytest.raises(OSError):
        store.write_payload(snapshot(20).model_dump_json())
    assert store.read().tick == 10


@pytest.mark.parametrize("envelope", [[], None, {"payload": None}, {"payload": 42}])
def test_malformed_envelope_falls_back(tmp_path, envelope):
    store = LocalRecovery(tmp_path / "world.gz")
    store.write_payload(snapshot(10).model_dump_json())
    store.write_payload(snapshot(20).model_dump_json())
    store.path.write_bytes(gzip.compress(json.dumps(envelope).encode()))
    assert store.read().tick == 10


@pytest.mark.asyncio
async def test_startup_restores_clock_and_calendar(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.application.services import recovery_service as service
    from app.infrastructure.api import dependencies

    path = tmp_path / "world.gz"
    LocalRecovery(path).write_payload(snapshot(123).model_dump_json())
    monkeypatch.setattr(service.settings, "LOCAL_RECOVERY_ENABLED", True)
    monkeypatch.setattr(service.settings, "LOCAL_RECOVERY_PATH", path)
    monkeypatch.setattr(service, "status", {})
    monkeypatch.setattr(dependencies, "get_world_service", lambda: SimpleNamespace(get_world=lambda: None))
    restored = []
    monkeypatch.setattr(dependencies, "restore_checkpoint_state", lambda *args: restored.append(args))
    calendars = []
    monkeypatch.setattr(service, "configure_calendar_control", lambda *args: calendars.append(args))
    await service.restore_recovery()
    assert restored[0][1:] == (123, 1)
    assert calendars[0][0] == 123
    assert service.status["state"] == "restored_paused"


@pytest.mark.asyncio
async def test_invalid_startup_preserves_file(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.application.services import recovery_service as service
    from app.infrastructure.api import dependencies

    path = tmp_path / "world.gz"
    path.write_bytes(b"broken")
    monkeypatch.setattr(service.settings, "LOCAL_RECOVERY_ENABLED", True)
    monkeypatch.setattr(service.settings, "LOCAL_RECOVERY_PATH", path)
    monkeypatch.setattr(service, "status", {})
    monkeypatch.setattr(dependencies, "get_world_service", lambda: SimpleNamespace(get_world=lambda: None))
    with pytest.raises(RuntimeError, match="Local recovery failed"):
        await service.restore_recovery()
    assert path.read_bytes() == b"broken"
    assert service.status["state"] == "restore_failed"
