"""Acceptance contracts across planning, transport, building and observation."""

from app.application.services.analytics_service import AnalyticsService
from app.domain.models.cognition import ActionType
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from tests.test_decisions import _systems
from app.application.services.entity_presentation import activity_details


def test_busy_route_becomes_paid_walkable_road() -> None:
    """A citizen turns observed traffic into a real, traversable structure."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Road builder", 5, 5, tags={"autonomous"})
    world = decisions._require_world()  # noqa: SLF001
    tile = world.retrieve_tile(5, 4)
    assert tile is not None
    tile.metadata["foot_traffic"] = 9
    store = Structure(
        structure_type=StructureType.STORAGE,
        x=6,
        y=5,
        builder_id=str(agent.id),
        work_required=1,
        progress=1,
    )
    world.structures[str(store.id)] = store
    world.inventories[str(agent.id)].add("stone", 2)
    _, action = decisions.decide(agent.id, 0)
    assert action.action_type == ActionType.BUILD
    assert action.target["structure_type"] == "road"
    for tick in range(1, 4):
        decisions.advance_all(tick)
    road = next(
        site
        for site in world.structures.values()
        if site.structure_type == StructureType.ROAD
    )
    assert road.completed
    assert world.inventories[str(agent.id)].carried == 0
    decisions._perception.observe(agent.id, 4)  # noqa: SLF001
    decisions._navigation.plan(agent.id, 5, 4, 4)  # noqa: SLF001
    decisions._navigation.advance_all(5)  # noqa: SLF001
    assert (agent.x, agent.y) == (5, 4)
    assert tile.metadata["foot_traffic"] == 10


def test_inspector_explains_infeasible_need_and_retains_outcome() -> None:
    """The admin feed exposes why a higher-priority need could not be met."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Stranded", 5, 5)
    assert agent.needs is not None
    agent.needs.thirst = 90
    agent.needs.energy = 5
    decisions.decide(agent.id, 0)
    record = entities.admin_overview()[0]
    assert record["decision_reason"]
    assert record["decision_trace"][0]["goal"] == "satisfy_thirst"
    assert record["decision_trace"][0]["blocked_by"]
    assert agent.metadata["recent_actions"][-1]["outcome"] == "completed"


def test_export_counts_communal_supplies_and_reports_real_buildings() -> None:
    """Depositing wood changes ownership without making it vanish from the UI."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Carrier", 5, 5)
    world = decisions._require_world()  # noqa: SLF001
    store = Structure(
        structure_type=StructureType.STORAGE,
        x=6,
        y=5,
        builder_id=str(agent.id),
        work_required=1,
        progress=1,
    )
    world.structures[str(store.id)] = store
    world.inventories[str(agent.id)].add("wood", 10)
    decisions._construction.transfer_storage(store.id, str(agent.id), "wood", 7)  # noqa: SLF001
    data = AnalyticsService(decisions._repository).export()  # noqa: SLF001
    assert data["economy"]["stock"]["wood"] == 10
    assert data["buildings"][0]["stockpile"]["items"]["wood"] == 7


def test_live_inspector_reports_remaining_route_and_sleep_destination() -> None:
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Walker", 5, 5)
    world = decisions._require_world()
    decisions._perception.observe(agent.id, 0)
    plan = decisions._navigation.plan(agent.id, 7, 5, 0)
    details = activity_details(world, agent)
    assert details["route"] == [list(point) for point in plan.path[1:]]
    assert details["route_status"] == "moving"
    agent.metadata.update(state="sleep", night_destination=[7, 5],
                          last_decision_reason="Recover until dawn", indoors=True)
    details = activity_details(world, agent)
    assert details["action"] == "sleep"
    assert details["action_target"] == {"x": 7, "y": 5}
    assert details["decision_reason"] == "Recover until dawn"
    assert not details["indoors"]  # A flag alone cannot create a shelter.
