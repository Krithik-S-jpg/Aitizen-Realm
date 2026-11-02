from app.application.services.habitat_service import advance, observe, journal
from app.domain.models.calendar import calendar_at_tick, DayPhase, Season
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import World
from tests.test_community_routines import community


def setup():
    world, citizen, _, decisions, _ = community()
    tree = ResourceNode(resource_type=ResourceType.TREE, x=5, y=5, quantity=50, capacity=50)
    world.add_resource(tree)
    calendar = calendar_at_tick(0).model_copy(update={"phase": DayPhase.DAY, "season": Season.SPRING, "weather_intensity": 0})
    advance(world, 0, calendar)
    bird = next(e for e in world.entities.values() if e.metadata.get("species") == "songbird")
    return world, citizen, tree, bird, calendar


def test_nesting_breeding_is_food_gated_bounded_and_saved():
    world, citizen, tree, bird, calendar = setup()
    for tick in range(2, 100, 2):
        advance(world, tick, calendar)
    assert not any(e.metadata.get("parent_id") for e in world.entities.values())
    for tick in range(100, 180, 2):
        bird.metadata["last_fed_day"] = tick // 24
        advance(world, tick, calendar)
    chicks = [e for e in world.entities.values() if e.metadata.get("parent_id")]
    assert len(chicks) == 1
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.ecology == world.ecology
    advance(restored, 180, calendar)
    assert len([e for e in restored.entities.values() if e.metadata.get("parent_id")]) == 1


def test_real_food_consumption_and_tree_loss_relocation():
    world, citizen, tree, bird, calendar = setup()
    plant = ResourceNode(resource_type=ResourceType.PLANT, x=5, y=5, quantity=5, capacity=5)
    world.add_resource(plant)
    bird.needs.hunger = 60
    advance(world, 2, calendar)
    assert plant.quantity == 4.5 and bird.needs.hunger == 40
    replacement = ResourceNode(resource_type=ResourceType.TREE, x=8, y=5, quantity=50, capacity=50)
    world.add_resource(replacement)
    old = bird.metadata["habitat_id"]
    tree.quantity = 0
    advance(world, 4, calendar)
    assert world.ecology["homes"][old]["status"] == "abandoned"
    assert bird.metadata["habitat_id"] != old
    assert abs(bird.x-5) + abs(bird.y-5) <= 1


def test_journal_is_observed_snapshot_not_omniscient_or_live_reference():
    world, citizen, tree, bird, calendar = setup()
    citizen.x, citizen.y = 15, 15
    observe(world, citizen, 1)
    assert not journal(world)
    citizen.x, citizen.y = 5, 5
    observe(world, citizen, 2)
    records = journal(world)
    assert len(records) == 1
    world.ecology["homes"][bird.metadata["habitat_id"]]["status"] = "abandoned"
    assert records[0]["status"] != "abandoned"
    observe(world, citizen, 3)
    assert journal(world)[0]["status"] == "abandoned"


def test_grazer_consumes_real_farm_food_and_ignores_empty_farms():
    from app.domain.models.entity import Entity, EntityKind
    from app.domain.models.needs import NeedsState
    from app.domain.models.structure import Structure, StructureType
    from app.application.services.animal_service import AnimalService
    world, _, _, decisions, _ = community()
    for citizen in world.entities.values():
        citizen.active = False
    deer = Entity(kind=EntityKind.ANIMAL, name="Deer", x=5, y=5,
                  needs=NeedsState(hunger=60), metadata={"species": "deer"})
    world.entities[str(deer.id)] = deer
    farm = Structure(structure_type=StructureType.FARM, x=5, y=5, builder_id="test", work_required=1, progress=1, crop_food=2)
    world.structures[str(farm.id)] = farm
    service = AnimalService(decisions._repository)
    service._decide(world, deer, DayPhase.DAY, Season.SUMMER, 1)
    assert farm.crop_food == 1 and deer.needs.hunger == 45
    service._decide(world, deer, DayPhase.DAY, Season.SUMMER, 2)
    assert farm.crop_food == 0
    service._decide(world, deer, DayPhase.DAY, Season.SUMMER, 3)
    assert farm.crop_food == 0
