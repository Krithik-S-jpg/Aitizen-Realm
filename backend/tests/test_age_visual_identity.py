import pytest
from app.application.services.entity_presentation import activity_details, visual_identity
from app.domain.models.entity import EntityKind
from tests.test_decisions import _systems


@pytest.mark.parametrize("years,gender,expected", [
    (0, "female", "family_infant"),
    (2, "male", "family_toddler_male"),
    (8, "female", "family_child_female"),
    (15, "male", "family_teen_male"),
    (15, "female", "family_teen_female"),
    (65, "male", "family_elder_male"),
    (65, "female", "family_elder_female"),
])
def test_age_visual_keeps_saved_identity(years, gender, expected):
    entities, decisions, _ = _systems()
    person = entities.create(EntityKind.AGENT, "Age test", 5, 5, gender=gender)
    original = person.avatar_id
    person.metadata["age_days"] = years * 365
    assert visual_identity(person) == expected
    assert activity_details(decisions._require_world(), person)["visual_avatar"] == expected
    assert person.avatar_id == original


def test_carried_child_keeps_child_art():
    entities, decisions, _ = _systems()
    adult = entities.create(EntityKind.AGENT, "Guardian", 5, 5)
    child = entities.create(EntityKind.AGENT, "Child", 5, 5, gender="female")
    child.metadata["age_days"] = 8 * 365
    adult.metadata["carrying_casualty"] = str(child.id)
    assert activity_details(decisions._require_world(), adult)["carried_avatar"] == "family_child_female"
