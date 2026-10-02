"""Explicit Supabase research archive API tests without hosted writes."""

from fastapi.testclient import TestClient

from app.infrastructure.api.v1.research import research_archive_store
from app.main import app


def test_research_archive_uses_authoritative_data() -> None:
    """Archive payload counts and world metadata come from backend state."""
    received = []

    class Store:
        async def save(self, archive: dict) -> str:
            received.append(archive)
            return archive["id"]

    app.dependency_overrides[research_archive_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/simulation/stop")
            world = client.get("/api/v1/world").json()
            response = client.post("/api/v1/research/archive")
            assert response.status_code == 201, response.text
            body = response.json()
            assert body["run_id"] == received[0]["id"]
            assert received[0]["world_seed"] == world["seed"]
            assert received[0]["world_width"] == world["width"]
            assert body["metrics"] == len(received[0]["metrics"])
            assert body["events"] == len(received[0]["events"])
    finally:
        app.dependency_overrides.pop(research_archive_store, None)


def test_research_archive_is_not_public() -> None:
    """No configured token means the archive endpoint fails closed."""
    with TestClient(app) as client:
        assert client.post("/api/v1/research/archive").status_code == 401
