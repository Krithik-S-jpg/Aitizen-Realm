"""Connected routines, cooperation and multi-citizen acceptance."""

from app.application.services.settlement_observation import settlement_reports
from app.application.services.settlement_service import SettlementService
from app.application.services.society_service import SocietyService
from app.application.services.world_service import WorldService
from app.domain.models.calendar import DayPhase, calendar_at_tick
from app.domain.models.cognition import ActionType, GoalType, TaskStatus
from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import TerrainType
from tests.test_decisions import _systems


def test_claim_released_for_sleep_and_other_worker_chooses_free_resource():
    """Sleep frees the claim, and a competing worker uses an available node."""
    entities, decisions, lifecycle = _systems()
    world = decisions._repository.get()
    world.resources.clear()
    first = entities.create(EntityKind.AGENT, "First", 5, 5, tags={"autonomous"})
    second = entities.create(EntityKind.AGENT, "Second", 5, 6)
    nodes = [
        ResourceNode(
            resource_type=ResourceType.STONE, x=6, y=y, quantity=50, capacity=50
        )
        for y in (5, 6)
    ]
    for node in nodes:
        world.add_resource(node)
    decisions._perception.observe(second.id, 0)
    nodes[0].reserve(str(first.id), 0, 100)
    target = decisions._resource_target(world, second, ResourceType.STONE)
    assert target["resource_id"] == str(nodes[1].id)
    lifecycle.start(
        first,
        GoalType.GATHER,
        ActionType.GATHER,
        0.6,
        "Gather stone",
        0,
        {"resource_id": str(nodes[0].id), "x": 5, "y": 5},
    )
    night = next(
        tick for tick in range(48) if calendar_at_tick(tick).phase == DayPhase.NIGHT
    )
    decisions.advance_all(night)
    assert first.metadata["state"] == "sleep"
    assert lifecycle.active(first.id) is None
    assert nodes[0].reserved_by is None


def test_evening_social_visit_records_real_relationship():
    """Conversation requires proximity and yields a real social bond."""
    entities, decisions, lifecycle = _systems()
    world = decisions._repository.get()
    first = entities.create(EntityKind.AGENT, "First", 5, 5, tags={"autonomous"})
    second = entities.create(EntityKind.AGENT, "Second", 5, 6)
    dusk = next(
        tick for tick in range(48) if calendar_at_tick(tick).phase == DayPhase.DUSK
    )
    first.metadata["decision_tick"] = dusk
    target = decisions._social_target(world, first)
    assert target["social_with"] == str(second.id)
    goal, action = lifecycle.start(
        first, GoalType.EXPLORE, ActionType.MOVE, 0.72, "Evening visit", dusk, target
    )
    for tick in range(dusk, dusk + 2):
        decisions._finish_at_target(world, first, goal, action, tick)
    assert action.status == TaskStatus.COMPLETED
    assert len(world.social_bonds) == 2
    first.needs.thirst = 90
    assert decisions._social_target(world, first) is None


def test_five_citizens_establish_camp_without_orders():
    """Five citizens sleep, survive and complete real construction autonomously."""
    entities, decisions, _ = _systems()
    world = decisions._repository.get()
    world.resources.clear()
    water = world.retrieve_tile(5, 6)
    water.terrain = TerrainType.WATER
    water.walkable = False
    for x in (3, 7, 10):
        for kind, y in [
            (ResourceType.TREE, 4),
            (ResourceType.STONE, 7),
            (ResourceType.REEDS, 9),
            (ResourceType.BUSH, 11),
        ]:
            world.add_resource(
                ResourceNode(
                    resource_type=kind,
                    x=x,
                    y=y,
                    quantity=200,
                    capacity=200,
                    produce_type="fruit" if kind == ResourceType.BUSH else None,
                    produce_quantity=150 if kind == ResourceType.BUSH else 0,
                    produce_capacity=150 if kind == ResourceType.BUSH else 0,
                )
            )
    citizens = [
        entities.create(
            EntityKind.AGENT, f"Citizen {index}", 5 + index, 5, tags={"autonomous"}
        )
        for index in range(5)
    ]
    slept = set()
    positions = {str(citizen.id): set() for citizen in citizens}
    society = SocietyService(decisions._repository)
    settlement = SettlementService(decisions._repository)
    for tick in range(480):
        WorldService(decisions._repository).advance_resources(tick)
        decisions._navigation.advance_all(tick)
        decisions._needs.advance_all(tick)
        society.advance_all(tick)
        settlement.advance_all(tick)
        decisions.advance_all(tick)
        settlement.advance_all(tick)
        for citizen in citizens:
            positions[str(citizen.id)].add((citizen.x, citizen.y))
            if citizen.metadata.get("state") == "sleep":
                slept.add(citizen.id)
        assert all(inv.carried <= inv.capacity for inv in world.inventories.values())
    assert all(citizen.active for citizen in citizens)
    assert len(slept) == 5
    assert all(len(value) > 3 for value in positions.values())
    assert any(site.completed for site in world.structures.values())
    assert (
        len(
            {
                action.entity_id
                for action in world.actions.values()
                if action.status == TaskStatus.COMPLETED
                and action.action_type == ActionType.BUILD
            }
        )
        >= 2
    )
    reports = settlement_reports(world)
    assert reports and sum(report["active_members"] for report in reports) == 5
    assert len(reports[0]["jobs"]) == 5
    assert reports[0]["households"]
    assert reports[0]["beds_total"] >= 4
    assert any(
        action.result.get("delivered")
        for action in world.actions.values()
        if action.action_type == ActionType.BUILD
    )
