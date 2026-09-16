"""Utility decisions and inspectable goal/action lifecycle tests."""

from app.application.services.construction_service import ConstructionService
from app.application.services.decision_service import DecisionService
from app.application.services.entity_service import EntityService
from app.application.services.goal_action_service import GoalActionService
from app.application.services.navigation_service import NavigationService
from app.application.services.needs_service import NeedsService
from app.application.services.perception_service import PerceptionService
from app.application.services.resource_service import ResourceService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.cognition import ActionType, GoalType, TaskStatus
from app.domain.models.entity import EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import StructureType
from app.domain.models.world import TerrainType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _systems() -> tuple[EntityService, DecisionService, GoalActionService]:
    repository = InMemoryWorldRepository()
    repository.save(WorldGenerator.generate_flat_world(16, 16))
    perception = PerceptionService(repository)
    needs = NeedsService(repository)
    navigation = NavigationService(repository)
    resources = ResourceService(repository)
    lifecycle = GoalActionService(repository)
    decisions = DecisionService(
        repository,
        perception,
        needs,
        navigation,
        resources,
        lifecycle,
        ConstructionService(repository),
    )
    return EntityService(repository), decisions, lifecycle


def test_utility_selects_rest_and_records_completed_lifecycle() -> None:
    """The strongest feasible need creates an explainable completed action."""
    entities, decisions, lifecycle = _systems()
    agent = entities.create(EntityKind.AGENT, "Tired", 5, 5)
    assert agent.needs is not None
    agent.needs.energy = 5.0

    options = decisions.evaluate(agent.id)
    assert options[0].goal_type == GoalType.REST
    goal, action = decisions.decide(agent.id, tick=4)
    assert goal.goal_type == GoalType.REST
    assert action.action_type == ActionType.REST
    assert goal.status == TaskStatus.COMPLETED
    assert action.result == {"energy_recovered": 18.0}
    assert agent.needs.energy == 23.0
    history = lifecycle.history(agent.id)
    assert history["goals"] == [goal]
    assert history["actions"] == [action]


def test_hungry_agent_eats_carried_food() -> None:
    """Inventory makes eating feasible and utility AI consumes it."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Hungry", 5, 5)
    assert agent.needs is not None
    agent.needs.hunger = 90.0
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    world.inventories[str(agent.id)].add("food", 3.0)

    goal, action = decisions.decide(agent.id, tick=2)
    assert goal.goal_type == GoalType.SATISFY_HUNGER
    assert action.action_type == ActionType.EAT
    assert agent.needs.hunger == 74.0
    assert world.inventories[str(agent.id)].items["food"] == 1.0


def test_thirsty_agent_drinks_from_adjacent_water() -> None:
    """A nearby water source makes the thirst action immediately feasible."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Thirsty", 5, 5)
    assert agent.needs is not None
    agent.needs.thirst = 90.0
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    water = world.retrieve_tile(6, 5)
    assert water is not None
    water.terrain = TerrainType.WATER
    water.walkable = False

    goal, action = decisions.decide(agent.id, tick=3)
    assert goal.goal_type == GoalType.SATISFY_THIRST
    assert action.action_type == ActionType.DRINK
    assert agent.needs.thirst == 55.0


def test_only_opted_in_agents_run_automatic_decisions() -> None:
    """The autonomous tag gates simulation-driven decisions."""
    entities, decisions, lifecycle = _systems()
    autonomous = entities.create(
        EntityKind.AGENT, "Autonomous", 5, 5, tags={"autonomous"}
    )
    manual = entities.create(EntityKind.AGENT, "Manual", 8, 8)

    decisions.advance_all(tick=1)
    assert lifecycle.history(autonomous.id)["goals"]
    assert lifecycle.history(manual.id)["goals"] == []


def test_infeasible_need_falls_back_to_next_utility_option() -> None:
    """High thirst without known water does not crash the decision tick."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Explorer", 5, 5)
    assert agent.needs is not None
    agent.needs.thirst = 95.0

    goal, action = decisions.decide(agent.id, tick=1)
    assert goal.goal_type == GoalType.EXPLORE
    assert action.action_type == ActionType.MOVE
    assert action.status == TaskStatus.RUNNING


def test_full_inventory_makes_agent_explore_instead_of_gathering_in_place() -> None:
    """A full pack must not trap autonomy in zero-yield gather loops."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Loaded Explorer", 5, 5)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    decisions._perception.observe(agent.id, 0)  # noqa: SLF001
    inventory = world.inventories[str(agent.id)]
    inventory.add("stone", inventory.capacity)

    goal, action = decisions.decide(agent.id, tick=1)

    assert goal.goal_type == GoalType.EXPLORE
    assert action.action_type == ActionType.MOVE
    assert (action.target["x"], action.target["y"]) != (agent.x, agent.y)


def test_agent_explores_when_known_resources_do_not_match_recipe_deficit() -> None:
    """Knowing only the wrong material must expand knowledge, not cause hoarding."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Purposeful Explorer", 5, 5)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    decisions._perception.observe(agent.id, 0)  # noqa: SLF001
    for resource in world.resources.values():
        resource.resource_type = ResourceType.STONE

    goal, action = decisions.decide(agent.id, tick=1)

    assert goal.goal_type == GoalType.EXPLORE
    assert action.action_type == ActionType.MOVE


def test_resource_actions_target_an_adjacent_interaction_tile() -> None:
    """Agents work beside physical nodes instead of standing inside or far away."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Gatherer", 5, 5)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    resource = ResourceNode(
        resource_type=ResourceType.TREE,
        x=7,
        y=5,
        quantity=20.0,
        capacity=20.0,
    )
    world.resources = {str(resource.id): resource}
    decisions._perception.observe(agent.id, 0)  # noqa: SLF001

    target = decisions._resource_target(  # noqa: SLF001
        world, agent, ResourceType.TREE
    )

    assert (target["resource_x"], target["resource_y"]) == (7, 5)
    assert (target["x"], target["y"]) == (6, 5)
    assert target["resource_type"] == "tree"


def test_autonomous_agent_crafts_tool_when_materials_are_ready() -> None:
    """Tool crafting emerges from utility scoring rather than a direct order."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Toolmaker", 5, 5)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    inventory = world.inventories[str(agent.id)]
    inventory.add("wood", 2.0)
    inventory.add("stone", 3.0)
    inventory.add("fiber", 1.0)

    goal, action = decisions.decide(agent.id, tick=1)

    assert goal.goal_type == GoalType.CRAFT
    assert action.action_type == ActionType.CRAFT
    assert action.status == TaskStatus.COMPLETED
    assert inventory.items == {"fiber": 1.0, "stone_axe": 1.0}


def test_autonomous_agent_constructs_shelter_over_time() -> None:
    """Affordable shelter becomes a persistent multi-tick construction project."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Builder", 5, 5, tags={"autonomous"})
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    inventory = world.inventories[str(agent.id)]
    inventory.add("wood", 20.0)
    inventory.add("stone", 5.0)

    goal, action = decisions.decide(agent.id, tick=1)
    assert goal.goal_type == GoalType.BUILD
    assert action.action_type == ActionType.BUILD
    assert action.progress_ratio < 1.0
    for tick in range(2, 36):
        decisions.advance_all(tick)

    shelter = next(iter(world.structures.values()))
    assert shelter.structure_type == StructureType.SHELTER
    assert shelter.completed
    assert action.status == TaskStatus.COMPLETED


def test_adjacent_agent_finishes_felling_then_collects_ground_timber() -> None:
    """Work must continue without a navigation plan and conserve harvested wood."""
    entities, decisions, lifecycle = _systems()
    agent = entities.create(EntityKind.AGENT, "Lumberjack", 5, 5)
    world = decisions._repository.get()  # noqa: SLF001
    assert world is not None
    tree = ResourceNode(
        resource_type=ResourceType.TREE, x=6, y=5, quantity=80, capacity=80
    )
    world.resources = {str(tree.id): tree}
    decisions._perception.observe(agent.id, 0)  # noqa: SLF001
    target = decisions._interaction_target(world, agent, tree)  # noqa: SLF001
    goal, action = lifecycle.start(
        agent, GoalType.GATHER, ActionType.CHOP, 1, "Timber", 0, target
    )
    decisions._begin(world, agent, goal, action, 0)  # noqa: SLF001
    assert action.progress > 0
    for tick in range(1, 7):
        decisions._continue(world, agent, goal, action, tick)  # noqa: SLF001
    assert action.status == TaskStatus.COMPLETED
    assert tree.visual_state == "fallen"
    inventory = world.inventories[str(agent.id)]
    assert inventory.items.get("wood", 0) == 0
    decisions._perception.observe(agent.id, 7)  # noqa: SLF001
    target = decisions._planned_resource_target(world, agent)  # noqa: SLF001
    assert target["resource_type"] == "log"
    goal, action = lifecycle.start(
        agent, GoalType.GATHER, ActionType.GATHER, 1, "Collect", 7, target
    )
    decisions._begin(world, agent, goal, action, 7)  # noqa: SLF001
    decisions._continue(world, agent, goal, action, 8)  # noqa: SLF001
    assert action.status == TaskStatus.COMPLETED
    assert inventory.items["wood"] == 2  # Exactly the next axe recipe's deficit.
    assert sum(node.quantity for node in world.resources.values()) == 78
