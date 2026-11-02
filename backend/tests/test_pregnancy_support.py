import pytest
from app.application.services.family_service import advance, pregnancy_status, caregiving
from app.application.services.group_expeditions import ready
from app.application.services.hunting import target
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from tests.test_decisions import _systems


def setup():
    entities, decisions, _ = _systems()
    mother = entities.create(EntityKind.AGENT, "Mother", 5, 5, gender="female")
    mother.metadata.update(age_days=30*365, pregnancy={"id": "pregnancy-test", "partner_id": "other", "started_age_days": 30*365-140, "due_age_days": 30*365+140})
    return entities, decisions, mother


def test_progress_needs_and_duplicate_tick():
    _, decisions, mother = setup()
    assert pregnancy_status(mother)["progress"] == .5
    assert pregnancy_status(mother)["trimester"] == 2
    advance(decisions._require_world(), 1)
    hunger = mother.needs.hunger
    advance(decisions._require_world(), 1)
    assert mother.needs.hunger == hunger


def test_light_duty_guards_and_recovery():
    _, decisions, mother = setup()
    world = decisions._require_world()
    assert not ready(world, mother, 1)
    with pytest.raises(ValueError, match="pregnancy"):
        target(decisions, world, mother)
    with pytest.raises(ValueError, match="pregnancy"):
        decisions._navigation.explore_underwater(mother.id, 1)
    mother.metadata.pop("pregnancy")
    mother.metadata["recovery_until_age"] = mother.metadata["age_days"]+42
    assert pregnancy_status(mother)["recovery_days"] == 42
    assert not ready(world, mother, 1)


def test_household_supplies_are_transferred_not_created():
    entities, decisions, mother = setup()
    world = decisions._require_world()
    child = entities.create(EntityKind.AGENT, "Child", 5, 5)
    child.metadata.update(age_days=100, guardian_id=str(mother.id))
    child.needs.hunger = child.needs.thirst = 50
    home = Structure(structure_type=StructureType.SHELTER, x=5, y=5, builder_id=str(mother.id), progress=1, work_required=1, bed_capacity=3, resident_ids=[str(mother.id), str(child.id)])
    home.stockpile.add("food", 3)
    home.stockpile.add("water", 3)
    world.structures[str(home.id)] = home
    assert caregiving(decisions, world, mother, 1)
    pack = world.inventories[str(mother.id)]
    assert pack.items["food"] + home.stockpile.items["food"] == 3
    assert pack.items["water"] + home.stockpile.items["water"] == 3
    assert pack.items["water"] == 2
