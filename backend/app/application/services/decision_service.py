"""Opt-in autonomous utility decisions and goal/action execution."""

from uuid import UUID

from app.application.services.construction_service import ConstructionService
from app.application.services.danger_memory import sheltered
from app.application.services.goal_action_service import GoalActionService
from app.application.services.navigation_service import NavigationService
from app.application.services.needs_service import NeedsService
from app.application.services.perception_service import PerceptionService
from app.application.services.resource_service import ResourceService
from app.application.services.society_service import SocietyService
from app.application.services.utility_service import UtilityService
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.calendar import DayPhase, calendar_at_tick, get_calendar_control
from app.domain.models.cognition import (
    Action,
    ActionType,
    Goal,
    GoalType,
    UtilityOption,
)
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.navigation import MovementStatus
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.structure import StructureType
from app.domain.models.world import World


class DecisionService:
    """Runs deterministic autonomy for entities explicitly tagged autonomous."""

    def __init__(
        self,
        repository: IWorldRepository,
        perception: PerceptionService,
        needs: NeedsService,
        navigation: NavigationService,
        resources: ResourceService,
        lifecycle: GoalActionService,
        construction: ConstructionService,
    ) -> None:
        """Initializes the controller from reusable simulation services."""
        self._repository = repository
        self._perception = perception
        self._needs = needs
        self._navigation = navigation
        self._resources = resources
        self._lifecycle = lifecycle
        self._construction = construction

    def evaluate(self, entity_id: UUID) -> list[UtilityOption]:
        """Scores current motives without changing entity state."""
        world = self._require_world()
        entity = self._agent(world, entity_id)
        knowledge = world.entity_knowledge[str(entity.id)]
        inventory = world.inventories[str(entity.id)]
        options = UtilityService.evaluate(entity, knowledge, inventory)
        unfinished = any(
            not site.completed and key in knowledge.structures
            for key, site in world.structures.items()
        )
        for option in options:
            if option.goal_type == GoalType.EXPLORE and self._social_target(
                world, entity
            ):
                option.score = max(option.score, 0.72)
                option.reason = (
                    "Needs are met; spend a short evening break with a neighbour."
                )
            if (
                option.goal_type == GoalType.BUILD
                and inventory.has(ConstructionService.BLUEPRINTS[StructureType.ROAD][0])
                and self._road_target(world, entity) is not None
            ):
                if option.score < 0.7:
                    option.score = 0.7
                    option.reason = "Pave a frequently used route with carried stone."
            if (
                option.goal_type == GoalType.REST
                and entity.needs
                and entity.needs.energy < 85
                and calendar_at_tick(int(entity.metadata.get("decision_tick", 0))).phase
                == DayPhase.NIGHT
            ):
                option.score = max(option.score, 0.65)
                option.reason = "It is night; return to shelter and recover energy."
            if (
                option.goal_type == GoalType.GATHER
                and any(
                    inventory.items.get(item, 0) >= 4
                    for item in ("food", "fruit", "mushroom")
                )
                and any(
                    other.active
                    and other.kind == EntityKind.AGENT
                    and other.id != entity.id
                    and other.needs
                    and other.needs.hunger >= 45
                    and entity.distance_squared_to(other.x, other.y)
                    <= entity.perception_radius**2
                    for other in world.entities.values()
                )
            ):
                option.score = max(option.score, 0.8)
                option.reason = "A hungry nearby citizen needs some of our spare food."
            if (
                entity.needs
                and option.goal_type == GoalType.SATISFY_HUNGER
                and entity.needs.hunger > 55
            ):
                option.score = max(option.score, 1.25)
            if (
                entity.needs
                and option.goal_type == GoalType.SATISFY_THIRST
                and entity.needs.thirst > 55
            ):
                option.score = max(option.score, 1.3)
            if option.goal_type == GoalType.SEEK_SAFETY and self._threats(
                world, entity
            ):
                option.score = 1.6
                option.reason = (
                    "Dangerous wildlife was seen nearby; move away and warn neighbours."
                )
                if entity.metadata.get("fear_memory_id") and entity.metadata.get("wildlife_warning", {}).get("expires", -1) >= entity.metadata.get("decision_tick", 0):
                    option.reason = "Remembered a recent wildlife attack; avoid its location and seek safety."
            if (
                option.goal_type == GoalType.SEEK_SAFETY
                and entity.needs
                and entity.needs.body_temperature_c < 36
            ):
                option.score = max(option.score, 0.95)
                option.reason = (
                    "Body temperature is falling; seek shelter or a fueled fire."
                )
            if option.goal_type == GoalType.BUILD and unfinished:
                option.score = max(option.score, 0.86)
                option.reason = (
                    "Finish a known construction site before spending more materials."
                )
            if (
                option.goal_type == GoalType.GATHER
                and inventory.carried >= inventory.capacity * 0.85
            ):
                option.score = max(option.score, 0.9)
                option.reason = "Unload the pack into shared storage."
        return sorted(options, key=lambda item: (-item.score, item.goal_type.value))

    def decide(self, entity_id: UUID, tick: int) -> tuple[Goal, Action]:
        """Selects and begins the highest-scoring currently feasible motive."""
        world = self._require_world()
        entity = self._agent(world, entity_id)
        active = self._lifecycle.active(entity.id)
        if active is not None:
            return active
        self._perception.observe(entity.id, tick)
        entity.metadata["decision_tick"] = tick
        neighbours = [
            other
            for other in world.entities.values()
            if other.active
            and other.kind == EntityKind.AGENT
            and other.needs
            and entity.distance_squared_to(other.x, other.y)
            <= entity.perception_radius**2
        ]
        entity.metadata["community_hunger"] = (
            sum(other.needs.hunger for other in neighbours if other.needs)
            / len(neighbours)
            if neighbours
            else 0.0
        )
        selected: tuple[UtilityOption, ActionType, dict[str, object]] | None = None
        trace: list[dict[str, object]] = []
        for option in self.evaluate(entity.id):
            try:
                action_type, target = self._action_for(world, entity, option.goal_type)
                if (
                    "x" in target
                    and "y" in target
                    and (entity.x, entity.y) != (target["x"], target["y"])
                ):
                    if (
                        self._navigation._find_path(
                            world, entity, int(str(target["x"])), int(str(target["y"]))
                        )
                        is None
                    ):  # noqa: SLF001
                        raise ValueError("No reachable known route to this action.")
                if "resource_id" in target:
                    self._resources.reserve(
                        UUID(str(target["resource_id"])), str(entity.id), tick, 20
                    )
                selected = (option, action_type, target)
                trace.append(
                    {
                        "goal": option.goal_type.value.lower(),
                        "score": option.score,
                        "reason": option.reason,
                        "selected": True,
                    }
                )
                break
            except ValueError as error:
                trace.append(
                    {
                        "goal": option.goal_type.value.lower(),
                        "score": option.score,
                        "reason": option.reason,
                        "selected": False,
                        "blocked_by": str(error),
                    }
                )
                continue
        entity.metadata["decision_trace"] = trace
        entity.metadata["last_decision_tick"] = tick
        if selected is None:
            raise ValueError("No utility option currently has a feasible action.")
        option, action_type, target = selected
        entity.metadata.pop("blocked_reason", None)
        entity.metadata["last_decision_reason"] = option.reason
        goal, action = self._lifecycle.start(
            entity,
            option.goal_type,
            action_type,
            option.score,
            option.reason,
            tick,
            target,
        )
        self._begin(world, entity, goal, action, tick)
        return goal, action

    def advance_all(self, tick: int) -> None:
        """Advances active actions, then decides for idle autonomous agents."""
        world = self._require_world()
        calendar = calendar_at_tick(tick)
        autonomous = sorted(
            (
                entity
                for entity in world.entities.values()
                if entity.active
                and entity.kind == EntityKind.AGENT
                and "autonomous" in entity.tags
            ),
            key=lambda item: str(item.id),
        )
        # Release work owned by dead/removed citizens before assigning new work.
        for actor_id in list(world.active_actions):
            actor = world.entities.get(actor_id)
            if actor is None or not actor.active:
                abandoned = self._lifecycle.active(UUID(actor_id))
                if abandoned is not None:
                    self._lifecycle.fail(
                        *abandoned, tick, "Worker is no longer active."
                    )
        for entity in autonomous:
            self._perception.observe(entity.id, tick)
            entity.metadata["decision_tick"] = tick
            threats = self._threats(world, entity)
            observed_threats = self._threats(world, entity, include_warning=False)
            if observed_threats:
                warning = {
                    "x": observed_threats[0][0],
                    "y": observed_threats[0][1],
                    "expires": tick + 8,
                }
                for neighbour in autonomous:
                    if entity.distance_squared_to(neighbour.x, neighbour.y) <= 36:
                        neighbour.metadata["wildlife_warning"] = warning.copy()
            active = self._lifecycle.active(entity.id)
            sleep_window = calendar.phase == DayPhase.NIGHT
            if sleep_window and self._follow_night_routine(
                world, entity, active, threats, tick
            ):
                continue
            # Reaching here means dawn OR a survival emergency interrupted sleep.
            if entity.metadata.get("state") in {
                "sleep",
                "seek_shelter",
            }:
                plan = world.movement_plans.get(str(entity.id))
                if plan is not None and plan.status == MovementStatus.MOVING:
                    plan.status = MovementStatus.CANCELLED
                entity.metadata.update({"state": "idle", "woke_at_tick": tick})
                entity.metadata.pop("sleeping_since_tick", None)
                entity.metadata.pop("sheltered_sleep", None)
                entity.metadata.pop("indoors", None)
                entity.metadata.pop("sleep_home_id", None)
                entity.metadata.pop("night_destination", None)
                entity.metadata.pop("suspended_action", None)
                if active is not None and {"x", "y"} <= active[1].target.keys():
                    destination = (
                        int(str(active[1].target["x"])),
                        int(str(active[1].target["y"])),
                    )
                    if destination != (entity.x, entity.y):
                        try:
                            self._navigation.plan(entity.id, *destination, tick)
                        except ValueError:
                            self._lifecycle.fail(
                                active[0],
                                active[1],
                                tick,
                                "Suspended job could not be resumed after sleep.",
                            )
                            active = None
            if (
                active
                and entity.needs
                and (
                    entity.needs.hunger >= 85
                    or entity.needs.thirst >= 85
                    or entity.needs.energy <= 10
                )
                and active[0].goal_type
                in {GoalType.BUILD, GoalType.GATHER, GoalType.EXPLORE, GoalType.CRAFT}
            ):
                self._lifecycle.fail(
                    active[0],
                    active[1],
                    tick,
                    "Interrupted to meet urgent survival needs.",
                )
                plan = world.movement_plans.get(str(entity.id))
                if plan is not None:
                    plan.status = MovementStatus.CANCELLED
                active = None
            if active and threats and active[0].goal_type != GoalType.SEEK_SAFETY:
                self._lifecycle.fail(
                    active[0],
                    active[1],
                    tick,
                    "Interrupted by nearby dangerous wildlife.",
                )
                plan = world.movement_plans.get(str(entity.id))
                if plan is not None:
                    plan.status = MovementStatus.CANCELLED
                active = None
            if active is None:
                try:
                    self.decide(entity.id, tick)
                except ValueError:
                    entity.metadata["blocked_reason"] = (
                        "No reachable known action; waiting for conditions to change."
                    )
            else:
                target = active[1].target
                if "resource_id" in target:
                    try:
                        self._resources.reserve(
                            UUID(str(target["resource_id"])), str(entity.id), tick, 20
                        )
                    except (ValueError, LookupError) as error:
                        self._lifecycle.fail(active[0], active[1], tick, str(error))
                        continue
                self._continue(world, entity, active[0], active[1], tick)

    def _follow_night_routine(
        self,
        world: World,
        entity: Entity,
        active: tuple[Goal, Action] | None,
        threats: list[tuple[int, int]],
        tick: int,
    ) -> bool:
        """Moves a safe citizen to shelter and keeps them asleep until dawn."""
        needs = entity.needs
        if (
            needs is None
            or threats
            or needs.hunger >= 82
            or needs.thirst >= 82
            or needs.health < 40
            or needs.body_temperature_c < 35
        ):
            return False
        if active is not None:
            self._lifecycle.fail(
                *active,
                tick,
                "Released work for the night; another citizen may claim it.",
            )
        plan = world.movement_plans.get(str(entity.id))
        try:
            safe = self._safe_target(world, entity)
        except ValueError:
            safe = {}
        if safe.get("purpose") == "shelter" and (
            int(str(safe["x"])),
            int(str(safe["y"])),
        ) != (
            entity.x,
            entity.y,
        ):
            destination = (int(str(safe["x"])), int(str(safe["y"])))
            if (
                plan is None
                or plan.status != MovementStatus.MOVING
                or (plan.destination_x, plan.destination_y) != destination
            ):
                try:
                    self._navigation.plan(entity.id, *destination, tick)
                except ValueError:
                    safe = {}
            if safe:
                entity.metadata.update(
                    {
                        "state": "seek_shelter",
                        "night_destination": list(destination),
                        "sleep_home_id": safe.get("home_id"),
                        "indoors": False,
                        "last_decision_reason": "Night has arrived; walking to an available bed.",
                    }
                )
                return True
        if plan is not None and plan.status == MovementStatus.MOVING:
            plan.status = MovementStatus.CANCELLED
        needs.rest(4.0)
        entity.metadata.update(
            {
                "state": "sleep",
                "last_decision_reason": (
                    "Night routine: recover energy until dawn "
                    "unless survival needs interrupt."
                ),
                "sleeping_since_tick": entity.metadata.get("sleeping_since_tick", tick),
                "sheltered_sleep": safe.get("purpose") == "shelter",
                "sleep_home_id": safe.get("home_id"),
                "sleep_bed_index": entity.metadata.get("bed_index"),
                "indoors": bool(safe.get("home_id")),
            }
        )
        return True

    def _begin(
        self, world: World, entity: Entity, goal: Goal, action: Action, tick: int
    ) -> None:
        try:
            if action.action_type == ActionType.EAT:
                inventory = world.inventories[str(entity.id)]
                item_type = str(action.target.get("item_type", "food"))
                amount = min(2.0, inventory.items.get(item_type, 0.0))
                if amount <= 0.0:
                    raise ValueError("No carried food is available.")
                self._needs.eat(entity.id, amount, item_type)
                self._lifecycle.complete(
                    goal,
                    action,
                    tick,
                    {"food_consumed": amount, "item_type": item_type},
                )
            elif action.action_type == ActionType.DRINK:
                self._needs.drink_from_environment(entity.id, 35.0)
                self._lifecycle.complete(goal, action, tick, {"hydration": 35.0})
            elif action.action_type == ActionType.REST:
                self._needs.rest(entity.id, 18.0)
                self._lifecycle.complete(goal, action, tick, {"energy_recovered": 18.0})
            elif action.action_type == ActionType.CRAFT:
                item_type = str(action.target["item_type"])
                self._resources.craft(str(entity.id), item_type)
                self._lifecycle.complete(
                    goal, action, tick, {"crafted": item_type, "quantity": 1.0}
                )
            elif action.action_type == ActionType.BUILD:
                site_x, site_y = int(action.target["x"]), int(action.target["y"])
                if "structure_id" in action.target:
                    site = world.structures[str(action.target["structure_id"])]
                    if abs(entity.x - site.x) + abs(entity.y - site.y) > 1:
                        self._navigation.plan(entity.id, site_x, site_y, tick)
                        return
                    self._advance_building(entity, goal, action, tick)
                    return
                if abs(entity.x - site_x) + abs(entity.y - site_y) > 1:
                    self._navigation.plan(entity.id, site_x, site_y, tick)
                    return
                structure_type = StructureType(
                    str(action.target["structure_type"]).upper()
                )
                structure = self._construction.start_site(
                    str(entity.id),
                    structure_type,
                    int(action.target["x"]),
                    int(action.target["y"]),
                )
                action.target["structure_id"] = str(structure.id)
                action.work_required = structure.work_required
                self._advance_building(entity, goal, action, tick)
            elif action.action_type in {
                ActionType.MOVE,
                ActionType.GATHER,
                ActionType.CHOP,
                ActionType.PLUCK,
            }:
                target_x = int(action.target["x"])
                target_y = int(action.target["y"])
                if (entity.x, entity.y) == (target_x, target_y):
                    self._finish_at_target(world, entity, goal, action, tick)
                else:
                    self._navigation.plan(entity.id, target_x, target_y, tick)
            else:
                self._lifecycle.complete(goal, action, tick)
        except (LookupError, ValueError, KeyError) as error:
            self._lifecycle.fail(goal, action, tick, str(error))

    def _continue(
        self, world: World, entity: Entity, goal: Goal, action: Action, tick: int
    ) -> None:
        if action.action_type == ActionType.BUILD:
            try:
                if "structure_id" not in action.target:
                    plan = self._navigation.get_plan(entity.id)
                    if plan.status == MovementStatus.ARRIVED:
                        self._begin(world, entity, goal, action, tick)
                    elif plan.status in {
                        MovementStatus.BLOCKED,
                        MovementStatus.CANCELLED,
                    }:
                        raise ValueError("Construction site cannot be reached.")
                    return
                site = world.structures[str(action.target["structure_id"])]
                if site.completed:
                    self._lifecycle.complete(
                        goal, action, tick, {"built": site.structure_type.value.lower()}
                    )
                    return
                if abs(entity.x - site.x) + abs(entity.y - site.y) > 1:
                    plan = self._navigation.get_plan(entity.id)
                    if plan.status in {
                        MovementStatus.BLOCKED,
                        MovementStatus.CANCELLED,
                    }:
                        raise ValueError("Construction job cannot be reached.")
                    return
                self._advance_building(entity, goal, action, tick)
            except (LookupError, ValueError, KeyError) as error:
                self._lifecycle.fail(goal, action, tick, str(error))
            return
        if action.action_type not in {
            ActionType.MOVE,
            ActionType.GATHER,
            ActionType.CHOP,
            ActionType.PLUCK,
        }:
            return
        try:
            if (entity.x, entity.y) == (action.target["x"], action.target["y"]):
                self._finish_at_target(world, entity, goal, action, tick)
                return
            plan = self._navigation.get_plan(entity.id)
            if plan.status == MovementStatus.ARRIVED:
                self._finish_at_target(world, entity, goal, action, tick)
            elif plan.status in {
                MovementStatus.BLOCKED,
                MovementStatus.CANCELLED,
            }:
                self._lifecycle.fail(
                    goal, action, tick, f"Route {plan.status.value.lower()}."
                )
        except (LookupError, ValueError) as error:
            self._lifecycle.fail(goal, action, tick, str(error))

    def _finish_at_target(
        self, world: World, entity: Entity, goal: Goal, action: Action, tick: int
    ) -> None:
        if "social_with" in action.target:
            neighbour = world.entities.get(str(action.target["social_with"]))
            if (
                neighbour is None
                or not neighbour.active
                or entity.distance_squared_to(neighbour.x, neighbour.y) > 2
            ):
                raise ValueError("Neighbour moved away; reassess the social visit.")
            entity.metadata["state"] = "socialize"
            action.progress += 1
            if action.progress < 2:
                return
            SocietyService(self._repository).register_interaction(
                entity.id, neighbour.id, tick
            )
            SocietyService(self._repository).register_interaction(
                neighbour.id, entity.id, tick
            )
            entity.metadata["last_social_tick"] = tick
            neighbour.metadata["last_social_tick"] = tick
            entity.metadata["state"] = "idle"
            self._lifecycle.complete(
                goal, action, tick, {"socialized_with": str(neighbour.id)}
            )
            return
        if "supply_site" in action.target:
            site = world.structures[str(action.target["supply_site"])]
            if abs(entity.x - site.x) + abs(entity.y - site.y) > 1:
                raise ValueError("Must stand beside the supply site.")
            inventory = world.inventories[str(entity.id)]
            if action.target.get("purpose") == "fuel":
                amount = min(4.0, inventory.items.get("wood", 0.0))
                if amount <= 0:
                    raise ValueError("No fuel remains in the pack.")
                inventory.consume({"wood": amount})
                site.fuel += amount
                result: dict[str, object] = {"fuel_added": amount}
            else:
                amount = min(
                    site.crop_food, inventory.capacity - inventory.carried, 6.0
                )
                if amount <= 0:
                    raise ValueError("No ripe crops or carrying capacity remains.")
                inventory.add("food", amount)
                site.crop_food -= amount
                result = {"harvested_food": amount}
            self._lifecycle.complete(goal, action, tick, result)
            return
        if "share_with" in action.target:
            receiver = world.entities[str(action.target["share_with"])]
            if (
                not receiver.active
                or entity.distance_squared_to(receiver.x, receiver.y) > 2
            ):
                raise ValueError("Recipient moved away; reassess the food delivery.")
            inventory = world.inventories[str(entity.id)]
            destination = world.inventories[str(receiver.id)]
            item = str(action.target["item"])
            amount = min(
                2.0,
                inventory.items.get(item, 0),
                destination.capacity - destination.carried,
            )
            if amount <= 0:
                raise ValueError("Food transfer is no longer possible.")
            inventory.consume({item: amount})
            destination.add(item, amount)
            self._lifecycle.complete(
                goal, action, tick, {"shared": amount, "recipient": str(receiver.id)}
            )
            return
        if "storage_id" in action.target:
            amount = self._construction.transfer_storage(
                UUID(str(action.target["storage_id"])),
                str(entity.id),
                str(action.target["material"]),
                float(action.target["amount"]),
                bool(action.target["withdraw"]),
            )
            self._lifecycle.complete(
                goal,
                action,
                tick,
                {
                    "transferred": amount,
                    "material": action.target["material"],
                    "withdraw": action.target["withdraw"],
                },
            )
            return
        if action.action_type in {
            ActionType.GATHER,
            ActionType.CHOP,
            ActionType.PLUCK,
        }:
            resource_id = UUID(str(action.target["resource_id"]))
            resource = world.resources.get(str(resource_id))
            if resource is None or resource.depleted:
                raise ValueError("The targeted resource is no longer available.")
            distance = abs(entity.x - resource.x) + abs(entity.y - resource.y)
            if distance != 1:
                raise ValueError("The agent must stand beside a resource to use it.")
            work_rate = 1.0
            inventory = world.inventories[str(entity.id)]
            if action.action_type == ActionType.CHOP:
                work_rate = (
                    2.5 if inventory.items.get("stone_axe", 0.0) >= 1.0 else 0.75
                )
            action.progress = min(action.work_required, action.progress + work_rate)
            if entity.needs is not None:
                entity.needs.energy = max(0.0, entity.needs.energy - work_rate * 0.35)
            if action.progress < action.work_required:
                action.result = {
                    "phase": "working",
                    "progress_ratio": action.progress_ratio,
                }
                return
            if action.action_type == ActionType.PLUCK:
                _, _, gathered = self._resources.pluck(resource_id, str(entity.id), 3.0)
            elif action.action_type == ActionType.CHOP:
                _, _, gathered = self._resources.chop(
                    resource_id, str(entity.id), 20.0, tick
                )
            else:
                self._resources.reserve(resource_id, str(entity.id), tick, 3)
                amount = min(5.0, float(action.target.get("amount", 5.0)))
                _, _, gathered = self._resources.gather(
                    resource_id, str(entity.id), amount, tick
                )
            self._lifecycle.complete(
                goal,
                action,
                tick,
                {
                    "felled_timber"
                    if action.action_type == ActionType.CHOP
                    else "gathered": gathered,
                    "method": action.action_type.value.lower(),
                },
            )
        elif goal.goal_type == GoalType.SATISFY_THIRST:
            self._needs.drink_from_environment(entity.id, 35.0)
            self._lifecycle.complete(goal, action, tick, {"hydration": 35.0})
        elif goal.goal_type == GoalType.REST:
            self._needs.rest(entity.id, 18.0)
            self._lifecycle.complete(goal, action, tick, {"energy_recovered": 18.0})
        else:
            self._lifecycle.complete(
                goal, action, tick, {"arrived": [entity.x, entity.y]}
            )

    def _action_for(
        self, world: World, entity: Entity, goal_type: GoalType
    ) -> tuple[ActionType, dict[str, object]]:
        if goal_type == GoalType.SATISFY_HUNGER:
            inventory = world.inventories[str(entity.id)]
            for item_type in ("fruit", "food", "mushroom", "meat"):
                if inventory.items.get(item_type, 0.0) > 0.0:
                    return ActionType.EAT, {"item_type": item_type}
            for item_type in ("fruit", "food", "mushroom", "meat"):
                stored = self._storage_trip(world, entity, item_type, 3, True)
                if stored:
                    return ActionType.MOVE, stored
            for site in world.structures.values():
                if (
                    str(site.id) in world.entity_knowledge[str(entity.id)].structures
                    and site.completed
                    and site.crop_food > 0
                ):
                    return ActionType.MOVE, self._site_target(
                        world, entity, site.id, "harvest"
                    )
            try:
                return ActionType.PLUCK, self._fruit_target(world, entity)
            except ValueError:
                try:
                    return ActionType.GATHER, self._resource_target(
                        world, entity, ResourceType.CARCASS
                    )
                except ValueError:
                    return ActionType.GATHER, self._resource_target(
                        world, entity, ResourceType.PLANT
                    )
        if goal_type == GoalType.SATISFY_THIRST:
            if self._beside_water(world, entity):
                return ActionType.DRINK, {}
            return ActionType.MOVE, self._water_target(world, entity)
        if goal_type == GoalType.REST:
            try:
                safe = self._safe_target(world, entity)
            except ValueError:
                safe = {}
            if safe.get("purpose") == "shelter" and (safe["x"], safe["y"]) != (
                entity.x,
                entity.y,
            ):
                return ActionType.MOVE, safe
            return ActionType.REST, {}
        if goal_type == GoalType.GATHER:
            inventory = world.inventories[str(entity.id)]
            if entity.needs and entity.needs.body_temperature_c < 36.5:
                for site in world.structures.values():
                    if (
                        str(site.id)
                        in world.entity_knowledge[str(entity.id)].structures
                        and site.completed
                        and site.structure_type == StructureType.CAMPFIRE
                        and site.fuel < 1
                    ):
                        if inventory.items.get("wood", 0) > 0:
                            return ActionType.MOVE, self._site_target(
                                world, entity, site.id, "fuel"
                            )
                        return ActionType.GATHER, self._resource_target(
                            world, entity, ResourceType.LOG
                        )
            for neighbour in world.entities.values():
                if (
                    neighbour.id == entity.id
                    or not neighbour.active
                    or neighbour.kind != EntityKind.AGENT
                    or neighbour.needs is None
                    or neighbour.needs.hunger < 45
                ):
                    continue
                if (
                    entity.distance_squared_to(neighbour.x, neighbour.y)
                    > entity.perception_radius**2
                ):
                    continue
                for item in ("food", "fruit", "mushroom", "meat"):
                    if inventory.items.get(item, 0) >= 4:
                        return ActionType.MOVE, {
                            "share_with": str(neighbour.id),
                            "item": item,
                            "x": neighbour.x,
                            "y": neighbour.y,
                        }
            target = self._planned_resource_target(world, entity)
            if "storage_id" in target:
                return ActionType.MOVE, target
            resource = world.resources[str(target["resource_id"])]
            action_type = (
                ActionType.CHOP
                if resource.resource_type == ResourceType.TREE
                else ActionType.GATHER
            )
            return action_type, target
        if goal_type == GoalType.CRAFT:
            inventory = world.inventories[str(entity.id)]
            for item_type in ("stone_axe", "stone_pickaxe", "basket"):
                if inventory.items.get(item_type, 0.0) >= 1.0:
                    continue
                recipe = ResourceService.CRAFTING_RECIPES[item_type]
                if inventory.has(recipe):
                    return ActionType.CRAFT, {"item_type": item_type}
            raise ValueError("No useful tool recipe is currently affordable.")
        if goal_type == GoalType.BUILD:
            knowledge = world.entity_knowledge[str(entity.id)]
            for site in sorted(
                world.structures.values(),
                key=lambda s: entity.distance_squared_to(s.x, s.y),
            ):
                if site.completed or str(site.id) not in knowledge.structures:
                    continue
                missing = site.missing_materials
                can_deliver = any(
                    world.inventories[str(entity.id)].items.get(material, 0.0) > 0.0
                    for material in missing
                )
                if missing and not can_deliver:
                    continue
                workers = sum(
                    1
                    for other in world.entities.values()
                    if other.active
                    and other.id != entity.id
                    and (job := self._lifecycle.active(other.id)) is not None
                    and job[1].target.get("structure_id") == str(site.id)
                )
                if workers >= 2:
                    continue
                access = self._site_target(world, entity, site.id, "build")
                return ActionType.BUILD, {
                    "structure_id": str(site.id),
                    "structure_type": site.structure_type.value.lower(),
                    "x": access["x"],
                    "y": access["y"],
                    "purpose": "deliver" if missing else "build",
                }
            inventory = world.inventories[str(entity.id)]
            existing = {
                structure.structure_type
                for key, structure in world.structures.items()
                if key in knowledge.structures
                and not (
                    structure.structure_type == StructureType.STORAGE
                    and structure.completed
                    and structure.stockpile.carried
                    >= structure.stockpile.capacity * 0.9
                )
            }
            # Nearby workers announce planned projects even before foundations exist.
            # This avoids several citizens simultaneously funding the same facility.
            for other in world.entities.values():
                if (
                    other.id == entity.id
                    or not other.active
                    or entity.distance_squared_to(other.x, other.y)
                    > entity.perception_radius**2
                ):
                    continue
                job = self._lifecycle.active(other.id)
                if job and job[1].action_type == ActionType.BUILD:
                    kind = job[1].target.get("structure_type")
                    if kind:
                        existing.add(StructureType(str(kind).upper()))
            road = self._road_target(world, entity)
            if road is not None and inventory.has(
                ConstructionService.BLUEPRINTS[StructureType.ROAD][0]
            ):
                return ActionType.BUILD, {
                    "structure_type": "road",
                    "x": road[0],
                    "y": road[1],
                }
            structure_type = next(
                (
                    candidate
                    for candidate in UtilityService.building_priorities(
                        entity, inventory
                    )
                    if candidate not in existing
                    and any(
                        inventory.items.get(material, 0.0) > 0.0
                        for material in ConstructionService.BLUEPRINTS[candidate][0]
                    )
                ),
                None,
            )
            if structure_type is None:
                raise ValueError(
                    "No construction site needs this citizen's supplies or work."
                )
            build_x, build_y = self._build_site(world, entity, structure_type)
            return ActionType.BUILD, {
                "structure_type": structure_type.value.lower(),
                "x": build_x,
                "y": build_y,
            }
        if goal_type == GoalType.SEEK_SAFETY:
            if (
                not self._threats(world, entity)
                and entity.needs
                and entity.needs.body_temperature_c < 36.5
            ):
                for site in world.structures.values():
                    if (
                        str(site.id)
                        in world.entity_knowledge[str(entity.id)].structures
                        and site.completed
                        and site.structure_type == StructureType.CAMPFIRE
                        and site.fuel < 1
                    ):
                        if world.inventories[str(entity.id)].items.get("wood", 0) > 0:
                            return ActionType.MOVE, self._site_target(
                                world, entity, site.id, "fuel"
                            )
                        try:
                            return ActionType.GATHER, self._resource_target(
                                world, entity, ResourceType.LOG
                            )
                        except ValueError:
                            return ActionType.CHOP, self._resource_target(
                                world, entity, ResourceType.TREE
                            )
            safe = self._safe_target(world, entity)
            if (
                not self._threats(world, entity)
                and entity.needs
                and entity.needs.body_temperature_c < 36.5
                and safe.get("purpose") != "shelter"
            ):
                # Exposed ground does not solve cold. Work toward real warmth.
                try:
                    return self._action_for(world, entity, GoalType.BUILD)
                except ValueError:
                    return self._action_for(world, entity, GoalType.GATHER)
            if safe.get("purpose") == "safety" and (safe["x"], safe["y"]) == (
                entity.x,
                entity.y,
            ):
                raise ValueError(
                    "Already on safe terrain; no safer destination is known."
                )
            return ActionType.MOVE, safe
        social = self._social_target(world, entity)
        return ActionType.MOVE, social or self._exploration_target(world, entity)

    @staticmethod
    def _social_target(world: World, entity: Entity) -> dict[str, object] | None:
        tick = int(entity.metadata.get("decision_tick", 0))
        needs = entity.needs
        if (
            needs is None
            or needs.hunger >= 40
            or needs.thirst >= 40
            or needs.energy < 45
            or needs.safety < 60
            or needs.body_temperature_c < 36
            or calendar_at_tick(tick).phase != DayPhase.DUSK
            or tick - int(entity.metadata.get("last_social_tick", -10000))
            < get_calendar_control().ticks_per_day
        ):
            return None
        neighbours = sorted(
            (
                other
                for other in world.entities.values()
                if other.id != entity.id
                and other.active
                and other.kind == EntityKind.AGENT
                and entity.distance_squared_to(other.x, other.y) <= 2
                and other.metadata.get("state") != "sleep"
            ),
            key=lambda other: str(other.id),
        )
        if not neighbours:
            return None
        return {"social_with": str(neighbours[0].id), "x": entity.x, "y": entity.y}

    def _advance_building(
        self, entity: Entity, goal: Goal, action: Action, tick: int
    ) -> None:
        structure_id = UUID(str(action.target["structure_id"]))
        site = self._require_world().structures[str(structure_id)]
        if abs(entity.x - site.x) + abs(entity.y - site.y) > 1:
            raise ValueError("Builder must be beside the construction site.")
        inventory = self._require_world().inventories[str(entity.id)]
        delivered: dict[str, float] = {}
        if site.missing_materials:
            delivered = self._construction.deliver_materials(
                structure_id, str(entity.id)
            )
            if site.missing_materials:
                self._lifecycle.complete(
                    goal,
                    action,
                    tick,
                    {
                        "phase": "delivery",
                        "delivered": delivered,
                        "still_needed": site.missing_materials,
                        "structure_id": str(site.id),
                    },
                )
                return
        # Construction remains multi-tick work, but a normal daylight window is
        # long enough to make visible progress before citizens sleep.
        work_rate = 2.0 if inventory.items.get("stone_axe", 0.0) >= 1.0 else 1.5
        structure = self._construction.apply_work(
            structure_id, str(entity.id), work_rate
        )
        action.progress = structure.progress
        if entity.needs is not None:
            entity.needs.energy = max(0.0, entity.needs.energy - work_rate * 0.3)
        if structure.completed:
            self._lifecycle.complete(
                goal,
                action,
                tick,
                {
                    "structure_id": str(structure.id),
                    "built": structure.structure_type.value.lower(),
                    "delivered": delivered,
                },
            )
        else:
            action.result = {
                "phase": "building",
                "progress_ratio": action.progress_ratio,
                "delivered": delivered,
            }

    @staticmethod
    def _resource_target(
        world: World, entity: Entity, preferred: ResourceType | None = None
    ) -> dict[str, object]:
        knowledge = world.entity_knowledge[str(entity.id)]
        candidates = [
            resource
            for key, resource in world.resources.items()
            if key in knowledge.resources
            and not resource.depleted
            and (
                not resource.is_reserved(int(entity.metadata.get("decision_tick", 0)))
                or resource.reserved_by == str(entity.id)
            )
            and (preferred is None or resource.resource_type == preferred)
        ]
        if not candidates:
            raise ValueError("No suitable known resource is available.")
        target = min(
            candidates,
            key=lambda item: (entity.distance_squared_to(item.x, item.y), str(item.id)),
        )
        return DecisionService._interaction_target(world, entity, target)

    @staticmethod
    def _planned_resource_target(world: World, entity: Entity) -> dict[str, object]:
        """Chooses a known resource that advances the next survival milestone."""
        inventory = world.inventories[str(entity.id)]
        milestones: list[dict[str, float]] = []
        unfinished_missing = [
            site.missing_materials
            for key, site in world.structures.items()
            if key in world.entity_knowledge[str(entity.id)].structures
            and not site.completed
            and site.missing_materials
        ]
        milestones.extend(unfinished_missing)
        if inventory.carried >= inventory.capacity * 0.85:
            for material, amount in sorted(
                inventory.items.items(), key=lambda item: -item[1]
            ):
                if material not in {
                    "wood",
                    "stone",
                    "fiber",
                    "ore",
                    "clay",
                    "fruit",
                    "food",
                }:
                    continue
                deposit = DecisionService._storage_trip(
                    world, entity, material, min(amount, 10.0), False
                )
                if deposit is not None:
                    return deposit
        if inventory.items.get("stone_axe", 0.0) < 1.0:
            milestones.append(ResourceService.CRAFTING_RECIPES["stone_axe"])
        if inventory.items.get("stone_pickaxe", 0.0) < 1.0:
            milestones.append(ResourceService.CRAFTING_RECIPES["stone_pickaxe"])
        if inventory.items.get("basket", 0.0) < 1.0:
            milestones.append(ResourceService.CRAFTING_RECIPES["basket"])
        existing_structures = {
            structure.structure_type
            for key, structure in world.structures.items()
            if key in world.entity_knowledge[str(entity.id)].structures
            and not (
                structure.structure_type == StructureType.STORAGE
                and structure.completed
                and structure.stockpile.carried >= structure.stockpile.capacity * 0.9
            )
        }
        next_structure = next(
            (
                structure_type
                for structure_type in UtilityService.building_priorities(
                    entity, inventory
                )
                if structure_type not in existing_structures
            ),
            None,
        )
        if next_structure is not None:
            milestones.append(ConstructionService.BLUEPRINTS[next_structure][0])
        elif DecisionService._road_target(world, entity) is not None:
            milestones.append(ConstructionService.BLUEPRINTS[StructureType.ROAD][0])

        resource_types = {
            "wood": {ResourceType.TREE, ResourceType.LOG, ResourceType.STUMP},
            "stone": {ResourceType.STONE},
            "fiber": {ResourceType.REEDS},
        }
        knowledge = world.entity_knowledge[str(entity.id)]
        has_missing_milestone_material = False
        for recipe in milestones:
            missing = sorted(
                (
                    (
                        max(0.0, amount - inventory.items.get(material, 0.0)) / amount,
                        material,
                    )
                    for material, amount in recipe.items()
                    if inventory.items.get(material, 0.0) < amount
                ),
                reverse=True,
            )
            has_missing_milestone_material = has_missing_milestone_material or bool(
                missing
            )
            for _, material in missing:
                stored = DecisionService._storage_trip(
                    world,
                    entity,
                    material,
                    recipe[material] - inventory.items.get(material, 0),
                    True,
                )
                if stored is not None:
                    return stored
                candidates = [
                    resource
                    for key, resource in world.resources.items()
                    if key in knowledge.resources
                    and not resource.depleted
                    and (
                        not resource.is_reserved(
                            int(entity.metadata.get("decision_tick", 0))
                        )
                        or resource.reserved_by == str(entity.id)
                    )
                    and resource.resource_type in resource_types.get(material, set())
                ]
                if material == "wood":
                    loose_timber = [
                        resource
                        for resource in candidates
                        if resource.resource_type == ResourceType.LOG
                    ]
                    candidates = loose_timber or [
                        resource
                        for resource in candidates
                        if resource.resource_type != ResourceType.TREE
                        or resource.growth >= 0.35
                    ]
                if candidates:
                    target = min(
                        candidates,
                        key=lambda item: (
                            entity.distance_squared_to(item.x, item.y),
                            str(item.id),
                        ),
                    )
                    interaction = DecisionService._interaction_target(
                        world, entity, target
                    )
                    interaction["material"] = material
                    interaction["amount"] = recipe[material] - inventory.items.get(
                        material, 0.0
                    )
                    return interaction
        for material in ("wood", "stone", "fiber", "ore", "clay"):
            retained = max(
                (recipe.get(material, 0) for recipe in milestones), default=0
            )
            spare = inventory.items.get(material, 0) - retained
            if spare > 0:
                deposit = DecisionService._storage_trip(
                    world, entity, material, spare, False
                )
                if deposit is not None:
                    return deposit
        if has_missing_milestone_material:
            raise ValueError(
                "The next required material is not known; exploration is needed."
            )
        raise ValueError(
            "All current material goals are satisfied; do not hoard surplus."
        )

    @staticmethod
    def _storage_trip(
        world: World, entity: Entity, material: str, amount: float, withdraw: bool
    ) -> dict[str, object] | None:
        knowledge = world.entity_knowledge[str(entity.id)]
        stores = sorted(
            world.structures.values(),
            key=lambda s: (entity.distance_squared_to(s.x, s.y), str(s.id)),
        )
        for store in stores:
            if (
                str(store.id) not in knowledge.structures
                or not store.completed
                or store.structure_type != StructureType.STORAGE
            ):
                continue
            if withdraw and store.stockpile.items.get(material, 0) <= 0:
                continue
            if not withdraw and store.stockpile.carried >= store.stockpile.capacity:
                continue
            spots = [
                (x, y)
                for x, y in (
                    (store.x + 1, store.y),
                    (store.x - 1, store.y),
                    (store.x, store.y + 1),
                    (store.x, store.y - 1),
                )
                if f"{x},{y}" in knowledge.tiles
                and (tile := world.retrieve_tile(x, y)) is not None
                and tile.walkable
                and not NavigationService._structure_blocks(world, x, y)
            ]  # noqa: SLF001
            if spots:
                x, y = min(spots, key=lambda p: entity.distance_squared_to(*p))
                return {
                    "storage_id": str(store.id),
                    "material": material,
                    "amount": amount,
                    "withdraw": withdraw,
                    "purpose": "withdraw" if withdraw else "deposit",
                    "x": x,
                    "y": y,
                }
        return None

    @staticmethod
    def _water_target(world: World, entity: Entity) -> dict[str, object]:
        knowledge = world.entity_knowledge[str(entity.id)]
        water = {"water", "ocean", "wetland"}
        candidates: list[tuple[int, int]] = []
        for record in knowledge.tiles.values():
            if record.data.get("terrain") not in water:
                continue
            for x, y in (
                (record.x + 1, record.y),
                (record.x - 1, record.y),
                (record.x, record.y + 1),
                (record.x, record.y - 1),
            ):
                known = knowledge.tiles.get(f"{x},{y}")
                if (
                    known is not None
                    and bool(known.data.get("walkable", False))
                    and not NavigationService._structure_blocks(world, x, y)
                ):  # noqa: SLF001
                    candidates.append((x, y))
        if not candidates:
            raise ValueError("No reachable known water source is available.")
        x, y = min(candidates, key=lambda pos: (entity.distance_squared_to(*pos), pos))
        return {"x": x, "y": y, "purpose": "drink"}

    @staticmethod
    def _fruit_target(world: World, entity: Entity) -> dict[str, object]:
        knowledge = world.entity_knowledge[str(entity.id)]
        candidates = [
            resource
            for key, resource in world.resources.items()
            if key in knowledge.resources
            and resource.produce_type == "fruit"
            and resource.produce_quantity > 0.0
            and (
                not resource.is_reserved(int(entity.metadata.get("decision_tick", 0)))
                or resource.reserved_by == str(entity.id)
            )
        ]
        if not candidates:
            raise ValueError("No ripe known fruit tree is available.")
        target = min(
            candidates,
            key=lambda item: (entity.distance_squared_to(item.x, item.y), str(item.id)),
        )
        return DecisionService._interaction_target(world, entity, target)

    @staticmethod
    def _interaction_target(
        world: World, entity: Entity, resource: ResourceNode
    ) -> dict[str, object]:
        """Returns a known walkable tile beside a physical resource node."""
        knowledge = world.entity_knowledge[str(entity.id)]
        candidates: list[tuple[int, int]] = []
        for x, y in (
            (resource.x + 1, resource.y),
            (resource.x - 1, resource.y),
            (resource.x, resource.y + 1),
            (resource.x, resource.y - 1),
        ):
            tile = world.retrieve_tile(x, y)
            if (
                f"{x},{y}" in knowledge.tiles
                and tile is not None
                and tile.walkable
                and not NavigationService._structure_blocks(world, x, y)
            ):  # noqa: SLF001
                candidates.append((x, y))
        if not candidates:
            raise ValueError("No known walkable tile is available beside the resource.")
        x, y = min(
            candidates,
            key=lambda point: (entity.distance_squared_to(*point), point),
        )
        return {
            "resource_id": str(resource.id),
            "resource_type": resource.resource_type.value.lower(),
            "resource_x": resource.x,
            "resource_y": resource.y,
            "x": x,
            "y": y,
        }

    @staticmethod
    def _site_target(
        world: World, entity: Entity, site_id: UUID, purpose: str
    ) -> dict[str, object]:
        site = world.structures[str(site_id)]
        knowledge = world.entity_knowledge[str(entity.id)]
        spots = [
            (site.x + dx, site.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if f"{site.x + dx},{site.y + dy}" in knowledge.tiles
            and (tile := world.retrieve_tile(site.x + dx, site.y + dy)) is not None
            and tile.walkable
            and not NavigationService._structure_blocks(world, site.x + dx, site.y + dy)
        ]  # noqa: SLF001
        if not spots:
            raise ValueError("No accessible known tile beside site.")
        x, y = min(spots, key=lambda p: entity.distance_squared_to(*p))
        return {"x": x, "y": y, "supply_site": str(site_id), "purpose": purpose}

    @staticmethod
    def _threats(
        world: World, entity: Entity, include_warning: bool = True
    ) -> list[tuple[int, int]]:
        if sheltered(world, entity):
            return []
        threats = [
            (other.x, other.y)
            for other in world.entities.values()
            if other.active
            and other.kind == EntityKind.ANIMAL
            and other.metadata.get("species") in {"wolf", "bear", "boar"}
            and entity.distance_squared_to(other.x, other.y)
            <= min(6, entity.perception_radius) ** 2
        ]
        warning = entity.metadata.get("wildlife_warning", {})
        if include_warning and warning.get("expires", -1) >= entity.metadata.get(
            "decision_tick", 0
        ):
            threats.append((int(warning["x"]), int(warning["y"])))
        return threats

    @staticmethod
    def _safe_target(world: World, entity: Entity) -> dict[str, object]:
        knowledge = world.entity_knowledge[str(entity.id)]
        threats = DecisionService._threats(world, entity)
        if threats:
            candidates = [
                record
                for record in knowledge.tiles.values()
                if record.data.get("walkable")
                and not NavigationService._structure_blocks(world, record.x, record.y)
            ]  # noqa: SLF001
            if candidates:
                target = max(
                    candidates,
                    key=lambda r: (
                        min((r.x - x) ** 2 + (r.y - y) ** 2 for x, y in threats),
                        -entity.distance_squared_to(r.x, r.y),
                    ),
                )
                return {"x": target.x, "y": target.y, "purpose": "avoid_wildlife"}
        assigned_home_id = str(entity.metadata.get("assigned_home_id", ""))
        assigned_home = world.structures.get(assigned_home_id)
        if assigned_home is None:
            available = [home for home in world.structures.values()
                         if home.completed and home.structure_type in {StructureType.SHELTER, StructureType.TENT}
                         and str(home.id) in knowledge.structures
                         and len(home.resident_ids) < home.bed_capacity]
            if available:
                assigned_home = min(available, key=lambda home: (entity.distance_squared_to(home.x, home.y), str(home.id)))
                assigned_home_id = str(assigned_home.id)
                assigned_home.resident_ids.append(str(entity.id))
                entity.metadata.update(assigned_home_id=assigned_home_id, bed_index=len(assigned_home.resident_ids) - 1, homeless=False)
        if (
            assigned_home is not None
            and assigned_home.completed
            and str(assigned_home.id) in knowledge.structures
            and str(entity.id) in assigned_home.resident_ids
        ):
            bed_spots = [
                (assigned_home.x + dx, assigned_home.y + dy)
                for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))
                if (
                    tile := world.retrieve_tile(
                        assigned_home.x + dx, assigned_home.y + dy
                    )
                )
                is not None
                and tile.walkable
                and not NavigationService._structure_blocks(world, tile.x, tile.y)
                and f"{assigned_home.x + dx},{assigned_home.y + dy}" in knowledge.tiles
            ]
            if bed_spots:
                index = int(entity.metadata.get("bed_index", 0)) % len(bed_spots)
                x, y = bed_spots[index]
                return {
                    "x": x,
                    "y": y,
                    "purpose": "shelter",
                    "home_id": assigned_home_id,
                    "bed_index": entity.metadata.get("bed_index", 0),
                }
        shelters = [
            structure
            for structure in world.structures.values()
            if structure.completed
            and str(structure.id) in knowledge.structures
            and (
                structure.structure_type in {StructureType.SHELTER, StructureType.TENT}
                or (
                    structure.structure_type == StructureType.CAMPFIRE
                    and structure.fuel > 0
                )
            )
        ]
        shelter_tiles = [
            (x, y)
            for shelter in shelters
            for x, y in (
                (shelter.x + 1, shelter.y),
                (shelter.x - 1, shelter.y),
                (shelter.x, shelter.y + 1),
                (shelter.x, shelter.y - 1),
            )
            if (tile := world.retrieve_tile(x, y)) is not None
            and tile.walkable
            and f"{x},{y}" in knowledge.tiles
        ]
        if shelter_tiles:
            x, y = min(
                shelter_tiles,
                key=lambda point: (entity.distance_squared_to(*point), point),
            )
            return {"x": x, "y": y, "purpose": "shelter"}
        safe = [
            record
            for record in knowledge.tiles.values()
            if record.data.get("terrain") in {"grass", "forest"}
            and bool(record.data.get("walkable", False))
        ]
        if not safe:
            raise ValueError("No known safer terrain is available.")
        target = min(safe, key=lambda item: entity.distance_squared_to(item.x, item.y))
        return {"x": target.x, "y": target.y, "purpose": "safety"}

    @staticmethod
    def _road_target(world: World, entity: Entity) -> tuple[int, int] | None:
        """Pave observed busy routes only after citizens establish infrastructure."""
        knowledge = world.entity_knowledge[str(entity.id)]
        known_sites = [
            site
            for key, site in world.structures.items()
            if key in knowledge.structures
        ]
        if not any(
            site.completed and site.structure_type == StructureType.STORAGE
            for site in known_sites
        ):
            return None
        occupied = {(site.x, site.y) for site in world.structures.values()}
        candidates = [
            record
            for record in knowledge.tiles.values()
            if int(record.data.get("foot_traffic", 0)) >= 8
            and record.data.get("walkable")
            and (record.x, record.y) not in occupied
            and not NavigationService._structure_blocks(world, record.x, record.y)
        ]  # noqa: SLF001
        if not candidates:
            return None
        chosen = min(
            candidates,
            key=lambda record: (
                -int(record.data["foot_traffic"]),
                entity.distance_squared_to(record.x, record.y),
            ),
        )
        return chosen.x, chosen.y

    @staticmethod
    def _build_site(
        world: World, entity: Entity, structure_type: StructureType | None = None
    ) -> tuple[int, int]:
        """Finds the nearest deterministic, vacant walkable construction tile."""
        occupied = {
            (structure.x, structure.y) for structure in world.structures.values()
        }
        blocked = {
            (resource.x, resource.y)
            for resource in world.resources.values()
            if not resource.depleted or resource.visual_state in {"fallen", "stump"}
        }
        for radius in range(1, 5):
            ring = [
                (entity.x + dx, entity.y + dy)
                for dy in range(-radius, radius + 1)
                for dx in range(-radius, radius + 1)
                if max(abs(dx), abs(dy)) == radius
            ]
            ring.sort(key=lambda point: (entity.distance_squared_to(*point), point))
            for x, y in ring:
                tile = world.retrieve_tile(x, y)
                if (
                    tile is not None
                    and tile.walkable
                    and (
                        structure_type != StructureType.FARM
                        or tile.terrain.value.lower() in {"grass", "meadow", "dirt"}
                    )
                    and (x, y) not in occupied
                    and (x, y) not in blocked
                ):
                    return x, y
        raise ValueError("No nearby vacant construction tile is available.")

    @staticmethod
    def _exploration_target(world: World, entity: Entity) -> dict[str, object]:
        knowledge = world.entity_knowledge[str(entity.id)]
        candidates = [
            record
            for record in knowledge.tiles.values()
            if bool(record.data.get("walkable", False))
            and (record.x, record.y) != (entity.x, entity.y)
        ]
        if not candidates:
            raise ValueError("No known exploration frontier is available.")
        target = max(
            candidates,
            key=lambda item: (
                entity.distance_squared_to(item.x, item.y),
                -item.last_seen_tick,
                item.key,
            ),
        )
        return {"x": target.x, "y": target.y, "purpose": "explore"}

    @staticmethod
    def _beside_water(world: World, entity: Entity) -> bool:
        return any(
            tile.terrain.value.lower() in {"water", "ocean", "wetland"}
            for tile in world.get_neighbors(entity.x, entity.y, include_diagonals=True)
        )

    @staticmethod
    def _agent(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        if not entity.active or entity.kind != EntityKind.AGENT:
            raise ValueError("Utility decisions require an active agent entity.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
