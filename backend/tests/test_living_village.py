from concurrent.futures import Future
from types import SimpleNamespace

from app.application.services.citizen_planner import CitizenPlanner
from app.application.services.society_service import SocietyService
from app.application.services.village_service import advance_village, upkeep_action
from app.application.services.village_service import discuss_project
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_community_routines import community


def test_llm_response_belongs_to_owner_not_next_citizen():
    world, a, b, _, _ = community()
    planner = CitizenPlanner()
    planner.last_submit = float("inf")
    planner.pending = Future()
    planner.pending.set_result({"goal": "BUILD", "rationale": "Need shelter"})
    planner.context = (world, a.id, 1, (a.x, a.y))
    options = [SimpleNamespace(goal_type=SimpleNamespace(value=x)) for x in ("REST", "BUILD")]
    assert planner.rank(world, b, options, 2, "test")[0].goal_type.value == "REST"
    assert planner.rank(world, a, options, 2, "test")[0].goal_type.value == "BUILD"
    planner.pool.shutdown(wait=False)


def test_daily_spoilage_is_idempotent_and_barter_conserves_goods():
    world, a, b, decisions, chat = community()
    b.x = 6
    SocietyService(decisions._repository).advance_all(1)
    source, destination = world.inventories[str(a.id)], world.inventories[str(b.id)]
    source.add("food", 10)
    source.add("wood", 2)
    destination.add("stone", 2)
    chat.barter(a.id, b.id, "wood", "stone", 1)
    assert source.items["wood"] == destination.items["wood"] == 1
    assert source.items["stone"] == destination.items["stone"] == 1
    advance_village(world, 1)
    advance_village(world, 25)
    amount = source.items["food"]
    assert 0 < amount < 10
    advance_village(world, 25)
    assert source.items["food"] == amount
    assert next(iter(world.groups.values())).village_story
    restored = World.model_validate_json(world.model_dump_json())
    advance_village(restored, 25)
    assert restored.inventories[str(a.id)].items["food"] == amount


def test_repair_costs_wood_and_recovery_yields_to_hunger():
    world, a, _, decisions, _ = community()
    site = Structure(structure_type=StructureType.SHELTER, builder_id=str(a.id),
                     x=5, y=6, work_required=1, progress=1, condition=80)
    world.structures[str(site.id)] = site
    decisions._perception.observe(a.id, 1)
    world.inventories[str(a.id)].add("wood", 1)
    assert upkeep_action(decisions, world, a, 1, [])
    assert site.condition == 90
    assert world.inventories[str(a.id)].items.get("wood", 0) == 0
    a.needs.health = 50
    a.needs.hunger = 80
    assert not upkeep_action(decisions, world, a, 2, [])
    a.needs.hunger = 0
    assert upkeep_action(decisions, world, a, 3, [])
    assert a.needs.health == 50.5


def test_first_aid_travels_and_consumes_fiber_once():
    world, a, b, decisions, _ = community()
    b.needs.health = 40
    world.inventories[str(a.id)].add("fiber", 2)
    decisions._perception.observe(a.id, 1)
    assert upkeep_action(decisions, world, a, 1, [])
    assert a.metadata["village_job"]["kind"] == "first_aid"
    assert b.needs.health == 40
    decisions._navigation.advance_all(2)
    assert upkeep_action(decisions, world, a, 2, [])
    assert b.needs.health == 45
    assert world.inventories[str(a.id)].items["fiber"] == 1
    assert not upkeep_action(decisions, world, a, 3, [])


def test_majority_project_is_real_and_completion_is_observed():
    world, a, b, decisions, chat = community()
    SocietyService(decisions._repository).advance_all(1)
    site = Structure(structure_type=StructureType.SHELTER, builder_id=str(a.id),
                     x=5, y=6, work_required=10)
    world.structures[str(site.id)] = site
    decisions._perception.observe(a.id, 1)
    assert discuss_project(chat, world, a, b, 2)
    group = next(iter(world.groups.values()))
    assert group.community_project["status"] == "agreed"
    assert len(group.community_project["votes"]) == 2
    assert site.progress == 0  # Agreement never constructs the building.
    assert not discuss_project(chat, world, a, b, 3)
    site.progress = 10
    advance_village(world, 4)
    assert group.community_project["status"] == "completed"
