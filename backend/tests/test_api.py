"""Integration tests for the Simulation Control API endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(api_client: TestClient) -> None:
    """Verifies that the root endpoint is online."""
    response = api_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Aitizen Realm"
    assert data["status"] == "online"


def test_simulation_state_endpoint(api_client: TestClient) -> None:
    """Verifies the /state retrieval endpoint."""
    response = api_client.get("/api/v1/simulation/state")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert data["current_tick"] == 0
    assert data["calendar"]["season"] == "SPRING"
    assert data["calendar"]["phase"] == "DAWN"
    assert data["world_health"]["resources"] >= 0
    assert 0.0 <= data["world_health"]["average_resource_ratio"] <= 1.0


def test_generated_world_contains_one_autonomous_player(api_client: TestClient) -> None:
    """Every playable world receives a backend-owned autonomous focus agent."""
    world = api_client.post("/api/v1/world/generate?seed=847291").json()
    players = [entity for entity in world["entities"] if "player" in entity["tags"]]
    assert len(players) == 1
    assert "autonomous" in players[0]["tags"]
    assert players[0]["needs"]["health"] == 100.0
    assert players[0]["goal"] == "idle"


def test_world_exposes_versioned_observation_layers(api_client: TestClient) -> None:
    """Observers can distinguish real layers from unimplemented systems."""
    payload = api_client.get("/api/v1/world").json()
    assert payload["schema_version"] == "1.0"
    assert payload["layer_support"]["terrain"] == "available"
    assert payload["layer_support"]["population"] == "available"
    assert payload["layer_support"]["wealth"] == "not_implemented"
    agent = payload["entities"][0]
    assert "knowledge" in agent
    assert "memory_count" in agent
    assert "relationship_count" in agent


def test_live_resource_endpoint_avoids_resending_the_entire_tile_grid(
    api_client: TestClient,
) -> None:
    """Frequent resource refreshes use a compact resource-only contract."""
    response = api_client.get("/api/v1/world/resources")
    assert response.status_code == 200
    resources = response.json()
    assert isinstance(resources, list)
    assert resources
    assert {"id", "type", "x", "y", "quantity"} <= resources[0].keys()


def test_citizen_observation_contract_uses_real_subsystem_state(
    api_client: TestClient,
) -> None:
    """Citizen inspection aggregates memory, actions, knowledge, and bonds."""
    world = api_client.get("/api/v1/world").json()
    entity_id = world["entities"][0]["id"]
    response = api_client.get(f"/api/v1/entities/{entity_id}/observation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["entity"]["id"] == entity_id
    assert payload["availability"]["memory"] == "available"
    assert payload["availability"]["mood"] == "not_implemented"


def test_simulation_lifecycle_endpoints(api_client: TestClient) -> None:
    """Tests starting, pausing, resuming, and stopping via API."""
    # 1. State is INITIALIZED or STOPPED initially
    resp = api_client.get("/api/v1/simulation/state")
    assert resp.json()["state"] in ["INITIALIZED", "STOPPED"]

    # 2. Start
    resp = api_client.post("/api/v1/simulation/start")
    assert resp.status_code == 200
    assert resp.json()["state"] == "RUNNING"

    # 3. Pause
    resp = api_client.post("/api/v1/simulation/pause")
    assert resp.status_code == 200
    assert resp.json()["state"] == "PAUSED"

    # 4. Resume
    resp = api_client.post("/api/v1/simulation/resume")
    assert resp.status_code == 200
    assert resp.json()["state"] == "RUNNING"

    # 5. Stop
    resp = api_client.post("/api/v1/simulation/stop")
    assert resp.status_code == 200
    assert resp.json()["state"] == "STOPPED"


def test_simulation_step_endpoint(api_client: TestClient) -> None:
    """Verifies stepping the simulation forward by 1 tick."""
    # Ensure starting from tick 0
    api_client.post("/api/v1/simulation/stop")

    resp = api_client.post("/api/v1/simulation/step")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] == 1

    resp = api_client.post("/api/v1/simulation/step")
    assert resp.json()["tick"] == 2


def test_simulation_tick_rate_endpoint(api_client: TestClient) -> None:
    """Verifies updating simulation speed via API."""
    # Set tick rate to 5.5
    resp = api_client.post("/api/v1/simulation/rate?ticks_per_second=5.5")
    assert resp.status_code == 200
    assert resp.json()["tick_rate"] == 5.5

    # Check that rate persists in state
    resp = api_client.get("/api/v1/simulation/state")
    assert resp.json()["tick_rate"] == 5.5

    # Invalid rate (Query gt=0.0 check will catch <= 0)
    resp = api_client.post("/api/v1/simulation/rate?ticks_per_second=-2.0")
    assert resp.status_code == 422  # query validation error


def test_cannot_step_via_api_while_running(api_client: TestClient) -> None:
    """Verifies that the /step endpoint rejects requests while simulation is running."""
    # Ensure it's running
    api_client.post("/api/v1/simulation/start")

    resp = api_client.post("/api/v1/simulation/step")
    assert resp.status_code == 400
    assert "Cannot manually step" in resp.json()["detail"]

    # Stop it to clean up
    api_client.post("/api/v1/simulation/stop")
