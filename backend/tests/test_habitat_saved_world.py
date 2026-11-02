"""Exercise real save/restore HTTP routes with isolated compressed storage."""
from copy import deepcopy
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.api import dependencies
from app.infrastructure.api.v1.checkpoints import checkpoint_store
from app.infrastructure.repositories.checkpoint_codec import encode_record, decode_record
from app.application.services.habitat_service import advance, observe
from tests.test_habitats import setup


def test_saved_habitat_world_restores_and_resumes_through_api():
    world, citizen, tree, bird, calendar = setup()
    observe(world, citizen, 0)
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
            dependencies._world_repository.save(world)
            response = client.post("/api/v1/checkpoints", json={"label": "Isolated habitat acceptance"})
            assert response.status_code == 201, response.text
            key = next(iter(records))
            world.ecology.clear()
            world.entities.pop(str(bird.id))
            restored_response = client.post(f"/api/v1/checkpoints/{key}/restore")
            assert restored_response.status_code == 200, restored_response.text
            restored = dependencies._world_repository.get()
            assert str(bird.id) in restored.entities
            assert restored.ecology["homes"]
            assert restored.entities[str(citizen.id)].metadata["wildlife_journal"]
            count = len(restored.entities)
            advance(restored, 2, calendar)
            assert len(restored.entities) == count  # No re-seeding birds on load.
            assert client.get("/api/v1/world/live").status_code == 200
    finally:
        app.dependency_overrides.pop(checkpoint_store, None)
        if previous is not None:
            dependencies._world_repository.save(previous)
