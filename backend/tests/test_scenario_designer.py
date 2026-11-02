import pytest
from pydantic import ValidationError
from app.application.services import scenario_service as service
from app.application.services.world_generator import WorldGenerator
from app.domain.models.scenario import ScenarioDefinition
from app.domain.models.world import World
from app.domain.models.entity import Entity, EntityKind


def definition(**changes):
    return ScenarioDefinition.model_validate({"name": "Rain expedition", "objectives": [{"id": "wait", "label": "Survive", "metric": "elapsed", "target": 10}], **changes})


def test_timeline_persists_without_duplicate_events():
    world = WorldGenerator.generate_flat_world(8, 8)
    design = definition(events=[{"id": "supply", "at_tick": 2, "kind": "resource", "choice": "BUSH", "x": 3, "y": 3}, {"id": "rain", "at_tick": 3, "kind": "weather", "choice": "RAIN", "x": 4, "y": 4}])
    key = service.save(world, design)
    service.start(world, key, 100)
    service.advance(world, 102)
    assert len(world.resources) == 1
    restored = World.model_validate_json(world.model_dump_json())
    service.advance(restored, 102)
    service.advance(restored, 103)
    assert len(restored.resources) == 1 and len(restored.weather_patches) == 1
    assert not restored.editor_history
    service.advance(restored, 110)
    assert restored.scenario_run["status"] == "completed"


@pytest.mark.parametrize("policy,status", [("skip", "running"), ("fail", "failed")])
def test_blocked_event_never_overwrites(policy, status):
    world = WorldGenerator.generate_flat_world(8, 8)
    citizen = Entity(kind=EntityKind.AGENT, name="Test", x=3, y=3)
    world.entities[str(citizen.id)] = citizen
    key = service.save(world, definition(events=[{"id": "supply", "kind": "resource", "choice": "TREE", "x": 3, "y": 3, "on_blocked": policy}]))
    service.start(world, key, 0)
    assert world.scenario_run["status"] == status
    assert not world.resources
    assert world.scenario_run["events"]["supply"] == "blocked"


def test_deadline_population_and_gated_event():
    world = WorldGenerator.generate_flat_world(8, 8)
    key = service.save(world, definition(deadline=3, events=[{"id": "note", "kind": "message", "after_objective": "wait", "message": "Ready"}]))
    service.start(world, key, 0)
    service.advance(world, 3)
    assert world.scenario_run["status"] == "failed"
    assert not world.scenario_run["events"]
    key = service.save(world, definition(minimum_population=1))
    service.start(world, key, 3)
    assert world.scenario_run["status"] == "failed"


def test_revision_and_running_definition_are_isolated():
    world = WorldGenerator.generate_flat_world(8, 8)
    key = service.save(world, definition())
    service.start(world, key, 0)
    service.save(world, definition(name="Edited"), key, 1)
    assert world.scenario_run["definition"]["name"] == "Rain expedition"
    with pytest.raises(ValueError):
        service.save(world, definition(), key, 1)
    with pytest.raises(ValueError):
        service.start(world, key, 0)


def test_validation_rejects_bad_references_and_outside_brush():
    with pytest.raises(ValidationError):
        definition(events=[{"id": "event", "kind": "message", "after_objective": "missing"}])
    with pytest.raises(ValidationError):
        definition(events=[{"id": "event", "kind": "weather", "choice": "BAD"}])
    with pytest.raises(ValidationError):
        definition(schema_version=2)
    with pytest.raises(ValueError):
        service.save(WorldGenerator.generate_flat_world(8, 8), definition(events=[{"id": "event", "kind": "weather", "choice": "RAIN", "x": 99}]))


def test_goal_condition_can_be_lost_and_event_gate_works():
    world = WorldGenerator.generate_flat_world(8, 8)
    citizen = Entity(kind=EntityKind.AGENT, name="Test", x=3, y=3)
    world.entities[str(citizen.id)] = citizen
    design = definition(objectives=[{"id": "population", "label": "Citizen", "metric": "population", "target": 1}, {"id": "wait", "label": "Wait", "metric": "elapsed", "target": 3}], events=[{"id": "hello", "kind": "message", "after_objective": "population", "message": "Hello"}])
    key = service.save(world, design)
    service.start(world, key, 0)
    assert world.scenario_run["events"]["hello"] == "applied"
    citizen.active = False
    service.advance(world, 3)
    assert world.scenario_run["status"] == "running"
    assert not world.scenario_run["objectives"]["population"]["met"]


def test_inventory_structure_and_exploration_metrics():
    from app.domain.models.inventory import Inventory
    from app.domain.models.structure import Structure, StructureType
    from app.domain.models.entity import EntityKnowledge
    from app.domain.models.scenario import Objective
    world = WorldGenerator.generate_flat_world(8, 8)
    citizen = Entity(kind=EntityKind.AGENT, name="Test", x=3, y=3)
    world.entities[str(citizen.id)] = citizen
    world.inventories[str(citizen.id)] = Inventory(items={"wood": 4})
    house = Structure(structure_type=StructureType.SHELTER, x=4, y=4, builder_id=str(citizen.id), progress=10, work_required=10, stockpile=Inventory(items={"wood": 6}))
    world.structures[str(house.id)] = house
    goal = Objective(id="g", label="Wood", metric="inventory", target=10, subject="wood")
    assert service.metric(world, goal, 0) == 10
    assert service.metric(world, goal.model_copy(update={"metric": "structures", "subject": "SHELTER"}), 0) == 1
    assert service.metric(world, goal.model_copy(update={"metric": "explored"}), 0) == 0
    house.condition = 0
    assert service.metric(world, goal, 0) == 4
