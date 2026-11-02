"""Isolated real simulation scenarios; hosted/user worlds are never modified."""
import os
import time
from types import SimpleNamespace
from concurrent.futures import Future
import pytest
from app.application.services.citizen_planner import CitizenPlanner, propose, set_ai_mode
from app.domain.models.entity import EntityKind
from app.domain.models.world import World
from tests.test_decisions import _systems


def test_modes_persist_for_multiple_citizens():
    entities, decisions, _ = _systems()
    a = entities.create(EntityKind.AGENT, "A", 5, 5)
    b = entities.create(EntityKind.AGENT, "B", 6, 5)
    world = decisions._require_world()
    set_ai_mode(world, a.id, "local_llm")
    set_ai_mode(world, b.id, "local_llm")
    assert a.metadata["ai_mode"] == "local_llm"
    assert b.metadata["ai_mode"] == "local_llm"
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.entities[str(b.id)].metadata["ai_mode"] == "local_llm"
    set_ai_mode(world, a.id, "utility")
    assert b.metadata["ai_mode"] == "local_llm"


@pytest.mark.skipif(os.environ.get("AITIZEN_LIVE_LLM_TEST") != "1", reason="Explicit local model integration run")
def test_two_citizens_receive_live_queued_proposals():
    entities, decisions, _ = _systems()
    citizens = [entities.create(EntityKind.AGENT, name, 5 + index, 5)
                for index, name in enumerate(("Aster", "Fern"))]
    world = decisions._require_world()
    pilot = CitizenPlanner()
    options = [SimpleNamespace(goal_type=SimpleNamespace(value="BUILD"))]
    received = set()
    deadline = time.monotonic() + 100
    try:
        while len(received) < 2 and time.monotonic() < deadline:
            for citizen in citizens:
                if citizen.id in received:
                    continue
                pilot.rank(world, citizen, options, 1, "qwen2.5:1.5b")
                if citizen.metadata.get("llm_planner", {}).get("goal") == "BUILD":
                    received.add(citizen.id)
                    pilot.waiting.pop(citizen.id, None)
            time.sleep(.05)
        assert len(received) == 2
    finally:
        pilot.pool.shutdown(wait=False, cancel_futures=True)


@pytest.mark.skipif(os.environ.get("AITIZEN_LIVE_LLM_TEST") != "1", reason="Explicit local model integration run")
@pytest.mark.parametrize("goal", ["SATISFY_HUNGER", "BUILD"])
def test_live_model_drives_real_action(goal, monkeypatch):
    import app.application.services.citizen_planner as module
    from app.core.config import settings
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Pilot", 5, 5, tags={"autonomous"})
    world = decisions._require_world()
    inventory = world.inventories[str(agent.id)]
    if goal == "SATISFY_HUNGER":
        agent.needs.hunger = 40
        inventory.add("food", 3)
    else:
        inventory.add("wood", 20)
        inventory.add("stone", 5)
    agent.metadata["ai_mode"] = "local_llm"
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")
    proposal = propose({"identity": "Pilot", "needs": agent.needs.model_dump(),
                        "allowed_goals": [goal], "memories": []}, settings.OLLAMA_MODEL)
    pilot = CitizenPlanner()
    pilot.pending = Future()
    pilot.pending.set_result(proposal)
    pilot.context = (world, agent.id, 1, (5, 5))
    pilot.last_submit = float("inf")
    monkeypatch.setattr(module, "planner", pilot)
    try:
        selected, action = decisions.decide(agent.id, 1)
        assert selected.goal_type.value == goal
        assert agent.metadata["llm_planner"]["goal"] == goal
        if goal == "SATISFY_HUNGER":
            assert agent.needs.hunger < 40
            assert inventory.items["food"] < 3
        else:
            for tick in range(2, 36):
                decisions.advance_all(tick)
            assert any(s.completed for s in world.structures.values())
            assert inventory.items.get("wood", 0) < 20
    finally:
        pilot.pool.shutdown(wait=False)
