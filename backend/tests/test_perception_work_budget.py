from app.domain.models.entity import EntityKind
from tests.test_decisions import _systems


def test_idle_tick_observes_each_citizen_once(monkeypatch):
    entities, decisions, _ = _systems()
    citizen = entities.create(EntityKind.AGENT, "Worker", 5, 5, tags={"autonomous"})
    citizen.metadata["age_days"] = 30*365
    calls = []
    original = decisions._perception.observe
    def tracked(entity_id, tick):
        calls.append((entity_id, tick))
        return original(entity_id, tick)
    monkeypatch.setattr(decisions._perception, "observe", tracked)
    decisions.advance_all(1)
    assert calls == [(citizen.id, 1)]


def test_direct_decision_still_observes(monkeypatch):
    entities, decisions, _ = _systems()
    citizen = entities.create(EntityKind.AGENT, "Worker", 5, 5)
    citizen.metadata["age_days"] = 30*365
    calls = []
    original = decisions._perception.observe
    def tracked(entity_id, tick):
        calls.append((entity_id, tick))
        return original(entity_id, tick)
    monkeypatch.setattr(decisions._perception, "observe", tracked)
    decisions.decide(citizen.id, 1)
    assert calls == [(citizen.id, 1)]
