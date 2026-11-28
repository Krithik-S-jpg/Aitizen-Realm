import pytest
from pydantic import ValidationError

from app.domain.models.appearance import CharacterAppearance
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.entity import CitizenAvatar


@pytest.mark.parametrize("avatar", [CitizenAvatar.ADULT_MALE, CitizenAvatar.ADULT_FEMALE])
def test_animated_base_survives_checkpoint(avatar):
    citizen = Entity(kind=EntityKind.AGENT, name="New base", x=2, y=3, avatar_id=avatar)
    assert Entity.model_validate_json(citizen.model_dump_json()).avatar_id == avatar


def test_old_citizens_keep_their_sprite_identity():
    citizen = Entity(kind=EntityKind.AGENT, name="Existing", x=2, y=3)
    assert citizen.appearance is None
    assert Entity.model_validate_json(citizen.model_dump_json()).avatar_id == citizen.avatar_id


def test_recipe_survives_save_roundtrip_independently_of_gender():
    citizen = Entity(kind=EntityKind.AGENT, name="New", x=2, y=3,
                     gender="nonbinary", appearance=CharacterAppearance(
                         base="female", eyes="hazel", hair="tied", clothing_color="#aabbcc"))
    restored = Entity.model_validate_json(citizen.model_dump_json())
    assert restored.appearance == citizen.appearance
    assert restored.gender == "nonbinary"


@pytest.mark.parametrize("change", [{"hair_color": "url(evil)"}, {"face": "missing"},
                                    {"version": 2}, {"target_citizen": "someone-else"}])
def test_recipe_rejects_unlisted_layers_and_invalid_colors(change):
    with pytest.raises(ValidationError):
        CharacterAppearance.model_validate({"base": "male", **change})
