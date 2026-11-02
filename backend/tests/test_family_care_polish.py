from app.application.services.family_service import care
from app.domain.models.entity import EntityKind
from tests.test_decisions import _systems


def family():
    entities, decisions, _ = _systems()
    parent = entities.create(EntityKind.AGENT, "Parent", 5, 5)
    child = entities.create(EntityKind.AGENT, "Child", 5, 5)
    parent.metadata["age_days"] = 30 * 365
    child.metadata.update(age_days=8*365, parent_ids=[str(parent.id)])
    return decisions._require_world(), parent, child


def test_food_does_not_create_water_and_water_is_consumed():
    world, parent, child = family()
    child.needs.hunger = child.needs.thirst = 50
    pack = world.inventories[str(parent.id)]
    pack.add("food", 1)
    care(world, child, [parent, child], 1)
    assert child.needs.thirst == 50
    pack.add("water", 1)
    care(world, child, [parent, child], 2)
    assert child.needs.thirst == 30
    assert pack.items.get("water", 0) == 0


def test_lessons_never_erase_skill_and_remote_guardian_is_assigned():
    world, parent, child = family()
    parent.skills["gathering"] = 1
    child.skills["gathering"] = 2
    care(world, child, [parent, child], 12)
    assert child.skills["gathering"] == 2
    assert parent.metadata["teaching_animation_until"] == 15
    parent.x = 10
    care(world, child, [parent, child], 13)
    assert child.metadata["guardian_id"] == str(parent.id)
    assert child.metadata["care_status"] == "Waiting for a nearby guardian"


def test_vegetarian_child_is_not_given_meat():
    world, parent, child = family()
    child.diet = "vegetarian"
    child.needs.hunger = 50
    world.inventories[str(parent.id)].add("cooked_meat", 1)
    care(world, child, [parent, child], 1)
    assert child.needs.hunger == 50
