import pytest
from tests.test_decisions import _systems
from app.application.services.fishing import advance
from app.domain.models.entity import EntityKind
from app.domain.models.cognition import ActionType, GoalType
from app.domain.models.world import TerrainType
from app.domain.models.structure import Structure, StructureType


def test_catch_cook_eat_uses_stock_inventory_and_fuel():
    entities, decisions, lifecycle = _systems()
    actor = entities.create(EntityKind.AGENT, "Fisher", 5, 5)
    world = decisions._require_world()
    tile = world.retrieve_tile(6, 5)
    tile.terrain = TerrainType.WATER
    tile.walkable = False
    inventory = world.inventories[str(actor.id)]
    inventory.add("fishing_rod", 1)
    goal, action = lifecycle.start(actor, GoalType.SATISFY_HUNGER, ActionType.FISH, .5, "Fish", 1,
        {"x":5,"y":5,"water_x":6,"water_y":5})
    for tick in range(1, 6):
        decisions._begin(world, actor, goal, action, tick) if tick == 1 else decisions._continue(world, actor, goal, action, tick)
    assert inventory.items["raw_fish"] == 1
    assert tile.metadata["fish_stock"] == 4
    fire = Structure(structure_type=StructureType.CAMPFIRE, x=4,y=5,builder_id=str(actor.id),work_required=1,progress=1,fuel=2)
    world.structures[str(fire.id)] = fire
    goal, action = lifecycle.start(actor, GoalType.SATISFY_HUNGER, ActionType.COOK, .5, "Cook", 6,
        {"x":5,"y":5,"cook_fire":str(fire.id)})
    for tick in range(6,9):
        decisions._begin(world, actor, goal, action, tick) if tick == 6 else decisions._continue(world, actor, goal, action, tick)
    assert inventory.items.get("raw_fish",0) == 0
    assert inventory.items["cooked_fish"] == 1
    assert fire.fuel == 1.5
    actor.needs.hunger = 70
    decisions.decide(actor.id, 9)
    assert actor.needs.hunger == 48
    assert inventory.items.get("cooked_fish",0) == 0


def test_fishing_without_rod_produces_nothing():
    entities, decisions, lifecycle = _systems()
    actor = entities.create(EntityKind.AGENT, "Fisher",5,5)
    world = decisions._require_world()
    world.retrieve_tile(6,5).terrain = TerrainType.WATER
    _, action = lifecycle.start(actor,GoalType.SATISFY_HUNGER,ActionType.FISH,.5,"Fish",1,{"water_x":6,"water_y":5})
    with pytest.raises(ValueError):
        advance(world,actor,action,1)
    assert not world.inventories[str(actor.id)].items
