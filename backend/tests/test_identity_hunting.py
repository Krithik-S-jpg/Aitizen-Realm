import pytest

from tests.test_decisions import _systems
from app.application.services import hunting
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.domain.models.cognition import ActionType, GoalType, TaskStatus
from app.domain.models.resource import ResourceType
from app.domain.models.structure import Structure, StructureType


def test_hunt_harvest_cook_eat_real_resources():
    entities, decisions, lifecycle = _systems()
    actor = entities.create(EntityKind.AGENT, "Hunter", 5, 5)
    world = decisions._require_world()
    prey = entities.create(EntityKind.ANIMAL, "Rabbit", 6, 5)
    prey.metadata["species"] = "rabbit"
    prey.needs = NeedsState()
    actor.needs.hunger = 70
    inventory = world.inventories[str(actor.id)]
    inventory.add("hunting_spear", 1)
    decisions._perception.observe(actor.id, 1)
    kind, target = hunting.target(decisions, world, actor)
    goal, action = lifecycle.start(actor, GoalType.SATISFY_HUNGER, kind, .8, "Hunt", 1, target)
    for tick in range(1, 4):
        hunting.advance(decisions, world, actor, goal, action, tick)
    assert action.status == TaskStatus.COMPLETED
    assert not prey.active
    assert inventory.items.get("meat", 0) == 0  # Must retrieve the carcass.
    carcass = next(r for r in world.resources.values() if r.resource_type == ResourceType.CARCASS)
    decisions._resources.reserve(carcass.id, str(actor.id), 4, 5)
    decisions._resources.gather(carcass.id, str(actor.id), 1, 4)
    assert inventory.items["meat"] == 1
    fire = Structure(structure_type=StructureType.CAMPFIRE, x=4, y=5,
                     builder_id=str(actor.id), work_required=1, progress=1, fuel=2)
    world.structures[str(fire.id)] = fire
    goal, action = lifecycle.start(actor, GoalType.SATISFY_HUNGER, ActionType.COOK,
        .8, "Cook meat", 5, {"x": 5, "y": 5, "cook_fire": str(fire.id), "ingredient": "meat"})
    for tick in range(5, 8):
        decisions._begin(world, actor, goal, action, tick) if tick == 5 else decisions._continue(world, actor, goal, action, tick)
    assert inventory.items.get("meat", 0) == 0
    assert inventory.items["cooked_meat"] == 1
    assert fire.fuel == 1.5
    decisions._needs.eat(actor.id, 1, "cooked_meat")
    assert actor.needs.hunger == 46


def test_vegetarian_rejects_meat_and_hunting_without_consumption():
    entities, decisions, _ = _systems()
    actor = entities.create(EntityKind.AGENT, "Vegetarian", 5, 5, diet="vegetarian")
    inventory = decisions._require_world().inventories[str(actor.id)]
    inventory.add("cooked_meat", 1)
    with pytest.raises(ValueError):
        decisions._needs.eat(actor.id, 1, "cooked_meat")
    with pytest.raises(ValueError):
        hunting.target(decisions, decisions._require_world(), actor)
    assert inventory.items["cooked_meat"] == 1


@pytest.mark.parametrize("avatar,gender", [("juniper", "female"), ("rowan", "male")])
def test_identity_round_trip_and_legacy_defaults(avatar, gender):
    actor = Entity(kind=EntityKind.AGENT, name=avatar.title(), x=1, y=1,
                   gender=gender, diet="vegetarian", avatar_id=avatar)
    restored = Entity.model_validate_json(actor.model_dump_json())
    assert (restored.gender, restored.diet, restored.avatar_id) == (gender, "vegetarian", avatar)
    legacy = actor.model_dump()
    del legacy["gender"], legacy["diet"]
    assert Entity.model_validate(legacy).diet == "omnivore"


def test_mild_warmth_does_not_accumulate_lethal_body_heat():
    needs = NeedsState()
    for _ in range(1000):
        needs.advance(25)
        needs.hunger = needs.thirst = 0
    assert 37 < needs.body_temperature_c < 38
    assert needs.health == 100
