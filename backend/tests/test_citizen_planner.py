from concurrent.futures import Future
from types import SimpleNamespace
from app.application.services.citizen_planner import CitizenPlanner


def test_langgraph_structured_proposal_with_mock_ollama(monkeypatch):
    import pytest
    pytest.importorskip("langgraph")
    import httpx
    from app.application.services.citizen_planner import propose
    original = httpx.Client
    def respond(request):
        return httpx.Response(200, json={"message": {"content": '{"goal":"BUILD","rationale":"Shelter needed"}'}})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    assert propose({"allowed_goals": ["BUILD"]}, "test")["goal"] == "BUILD"
    with pytest.raises(ValueError):
        propose({"allowed_goals": ["EAT"]}, "test")


def test_stale_world_response_cannot_control_restored_citizen():
    planner = CitizenPlanner()
    entity = SimpleNamespace(id="one", x=1, y=1, needs=SimpleNamespace(health=100, hunger=0, thirst=0, energy=100), metadata={})
    options = [SimpleNamespace(goal_type=SimpleNamespace(value="BUILD"))]
    planner.pending = Future()
    planner.pending.set_result({"goal": "BUILD", "rationale": "test"})
    planner.context = (object(), "one", 1, (1, 1))
    planner.last_submit = float("inf")
    entity.needs.model_dump = lambda **kwargs: {}
    entity.name = "One"
    entity.gender = "unspecified"
    entity.diet = "omnivore"
    assert planner.rank(SimpleNamespace(episodes={}), entity, options, 2, "test") == options
    assert "discarded" in entity.metadata["llm_planner"]["status"]
    planner.pool.shutdown(wait=False)
