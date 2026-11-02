"""HTTP lifecycle and compressed checkpoint acceptance without touching hosted saves."""
from copy import deepcopy
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.api import dependencies
from app.infrastructure.api.v1.checkpoints import checkpoint_store
from app.infrastructure.repositories.checkpoint_codec import encode_record, decode_record
from app.application.services.world_generator import WorldGenerator


def test_designer_api_checkpoint_resume_and_validation():
    records = {}

    class Store:
        async def save(self, record):
            records[record["id"]] = encode_record(deepcopy(record))
            return {"id": record["id"]}

        async def read(self, key=None):
            return [decode_record(deepcopy(record)) for identity, record in records.items() if key is None or str(identity) == str(key)]

    previous = dependencies._world_repository.get()
    app.dependency_overrides[checkpoint_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            world = WorldGenerator.generate_flat_world(8, 8)
            dependencies._world_repository.save(world)
            definition = {"name": "Acceptance", "objectives": [{"id": "wait", "label": "Wait", "metric": "elapsed", "target": 3}], "events": [{"id": "hello", "kind": "message", "message": "Arrival", "at_tick": 0}]}
            response = client.post("/api/v1/world/scenarios", json={"operation": "save", "definition": definition})
            assert response.status_code == 200, response.text
            key = response.json()["selected"]
            assert client.post("/api/v1/world/scenarios", json={"operation": "start", "scenario_id": key}).status_code == 200
            response = client.post("/api/v1/checkpoints", json={"label": "Scenario isolated acceptance"})
            assert response.status_code == 201, response.text
            world.scenario_run.clear()
            world.scenarios.clear()
            response = client.post(f"/api/v1/checkpoints/{next(iter(records))}/restore")
            assert response.status_code == 200, response.text
            state = client.get("/api/v1/world/scenarios").json()
            assert key in state["scenarios"]
            assert state["run"]["events"] == {"hello": "applied"}
            restored = dependencies._world_repository.get()
            for _ in range(3):
                stepped = client.post("/api/v1/simulation/step")
                assert stepped.status_code == 200, stepped.text
            assert restored.scenario_run["status"] == "completed"
            assert len([e for e in restored.scenario_run["history"] if "hello:" in e["message"]]) == 1
            bad = {**definition, "schema_version": 99}
            assert client.post("/api/v1/world/scenarios", json={"operation": "save", "definition": bad}).status_code == 422
            assert client.post("/api/v1/world/scenarios", json={"operation": "delete", "scenario_id": key, "revision": 0}).status_code == 409
            assert client.post("/api/v1/world/scenarios", json={"operation": "delete", "scenario_id": key, "revision": 1}).status_code == 200
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)
        if previous is not None:
            dependencies._world_repository.save(previous)
