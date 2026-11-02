import pytest
from app.application.services.family_service import caregiving, synchronize_infants
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_decisions import _systems


def setup():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    guardian = entities.create(EntityKind.AGENT, "Guardian", 5, 5)
    child = entities.create(EntityKind.AGENT, "Infant", 5, 5)
    guardian.metadata["age_days"] = 30*365
    child.metadata.update(age_days=100, guardian_id=str(guardian.id), parent_ids=[str(guardian.id)])
    home = Structure(structure_type=StructureType.SHELTER, x=8, y=5, progress=1, work_required=1, builder_id=str(guardian.id), bed_capacity=3, resident_ids=[str(guardian.id), str(child.id)])
    world.structures[str(home.id)] = home
    decisions._perception.observe(guardian.id, 1)
    return world, decisions, guardian, child


def test_pickup_moves_with_actual_route_and_releases_at_home():
    world, decisions, guardian, child = setup()
    assert caregiving(decisions, world, guardian, 1)
    assert child.metadata["infant_carried_by"] == str(guardian.id)
    with pytest.raises(ValueError):
        decisions._navigation.plan(child.id, 8, 5, 1)
    for tick in range(2, 8):
        decisions._navigation.advance_all(tick)
        synchronize_infants(world)
        assert (child.x, child.y) == (guardian.x, guardian.y)
        caregiving(decisions, world, guardian, tick)
        if not guardian.metadata.get("carrying_infant"):
            break
    assert guardian.distance_squared_to(8,5) <= 2
    assert not child.metadata.get("infant_carried_by")


def test_saved_transport_and_loss_of_carrier():
    world, decisions, guardian, child = setup()
    caregiving(decisions, world, guardian, 1)
    restored = World.model_validate_json(world.model_dump_json())
    carrier = restored.entities[str(guardian.id)]
    infant = restored.entities[str(child.id)]
    synchronize_infants(restored)
    assert infant.metadata["infant_carried_by"] == str(carrier.id)
    carrier.active = False
    position = (infant.x, infant.y)
    synchronize_infants(restored)
    assert not infant.metadata.get("infant_carried_by")
    assert not carrier.metadata.get("carrying_infant")
    assert (infant.x, infant.y) == position


def test_child_route_requires_supervision_and_stops_when_guardian_leaves():
    world, decisions, guardian, child = setup()
    child.metadata["age_days"] = 5*365
    decisions._perception.observe(child.id, 1)
    with pytest.raises(ValueError, match="guardian"):
        decisions._navigation.plan(child.id, 9, 5, 1)
    plan = decisions._navigation.plan(child.id, 6, 5, 1)
    guardian.x = 12
    decisions._navigation.advance_all(2)
    assert plan.status.value == "CANCELLED"
    assert (child.x, child.y) == (5,5)
