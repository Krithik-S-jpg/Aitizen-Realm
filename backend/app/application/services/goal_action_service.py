"""Lifecycle management for inspectable goals and actions."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.cognition import Action, ActionType, Goal, GoalType, TaskStatus
from app.domain.models.entity import Entity
from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.world import World


class GoalActionService:
    """Creates and transitions one active goal/action pair per entity."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes lifecycle state against the world repository."""
        self._repository = repository

    def start(
        self,
        entity: Entity,
        goal_type: GoalType,
        action_type: ActionType,
        utility_score: float,
        reason: str,
        tick: int,
        target: dict[str, object] | None = None,
    ) -> tuple[Goal, Action]:
        """Starts a new goal and its first action."""
        world = self._require_world()
        if str(entity.id) in world.active_goals:
            raise ValueError("Entity already has an active goal.")
        goal = Goal(
            entity_id=entity.id,
            goal_type=goal_type,
            utility_score=utility_score,
            reason=reason,
            created_at_tick=tick,
            status=TaskStatus.RUNNING,
            target=target or {},
        )
        action = Action(
            entity_id=entity.id,
            goal_id=goal.id,
            action_type=action_type,
            created_at_tick=tick,
            status=TaskStatus.RUNNING,
            target=target or {},
            work_required={
                ActionType.CHOP: 5.0,
                ActionType.GATHER: 2.0,
                ActionType.PLUCK: 1.0,
            }.get(action_type, 0.0),
        )
        world.goals[str(goal.id)] = goal
        world.actions[str(action.id)] = action
        world.active_goals[str(entity.id)] = str(goal.id)
        world.active_actions[str(entity.id)] = str(action.id)
        return goal, action

    def active(self, entity_id: UUID) -> tuple[Goal, Action] | None:
        """Returns the current goal/action pair, if one exists."""
        world = self._require_world()
        goal_id = world.active_goals.get(str(entity_id))
        action_id = world.active_actions.get(str(entity_id))
        if goal_id is None or action_id is None:
            return None
        return world.goals[goal_id], world.actions[action_id]

    def complete(
        self,
        goal: Goal,
        action: Action,
        tick: int,
        result: dict[str, object] | None = None,
    ) -> None:
        """Completes an active pair and retains it as history."""
        goal.status = TaskStatus.COMPLETED
        goal.completed_at_tick = tick
        action.status = TaskStatus.COMPLETED
        action.completed_at_tick = tick
        action.result = result or {}
        self._remember_result(goal, action, tick, True)
        self._clear_active(goal.entity_id)

    def fail(self, goal: Goal, action: Action, tick: int, reason: str) -> None:
        """Fails an active pair with an inspectable explanation."""
        goal.status = TaskStatus.FAILED
        goal.completed_at_tick = tick
        action.status = TaskStatus.FAILED
        action.completed_at_tick = tick
        action.failure_reason = reason
        self._remember_result(goal, action, tick, False)
        self._clear_active(goal.entity_id)

    def history(self, entity_id: UUID) -> dict[str, list[Goal] | list[Action]]:
        """Returns chronological goals and actions for one entity."""
        world = self._require_world()
        goals = [goal for goal in world.goals.values() if goal.entity_id == entity_id]
        actions = [
            action for action in world.actions.values() if action.entity_id == entity_id
        ]
        return {
            "goals": sorted(goals, key=lambda item: item.created_at_tick),
            "actions": sorted(actions, key=lambda item: item.created_at_tick),
        }

    def _clear_active(self, entity_id: UUID) -> None:
        world = self._require_world()
        # A completed/interrupted worker must not hold a harvest site hostage.
        action = world.actions.get(world.active_actions.get(str(entity_id), ""))
        if action is not None:
            resource = world.resources.get(str(action.target.get("resource_id", "")))
            if resource is not None and resource.reserved_by == str(entity_id):
                resource.release(str(entity_id))
        world.active_goals.pop(str(entity_id), None)
        world.active_actions.pop(str(entity_id), None)

    def _remember_result(
        self, goal: Goal, action: Action, tick: int, succeeded: bool
    ) -> None:
        world = self._require_world()
        entity = world.entities.get(str(goal.entity_id))
        if entity is None:
            return
        skill = {
            ActionType.CHOP: "woodcutting",
            ActionType.GATHER: "foraging",
            ActionType.PLUCK: "foraging",
            ActionType.BUILD: "building",
            ActionType.CRAFT: "crafting",
            ActionType.MOVE: "exploration",
        }.get(action.action_type)
        if skill is not None:
            experience = 2.0 if succeeded else 0.35
            entity.skills[skill] = min(
                100.0, entity.skills.get(skill, 0.0) + experience
            )
        outcome = "completed" if succeeded else "failed"
        recent = entity.metadata.setdefault("recent_actions", [])
        recent.append(
            {
                "tick": tick,
                "action": action.action_type.value.lower(),
                "outcome": outcome,
                "reason": goal.reason,
                "result": action.result,
                "failure": action.failure_reason,
            }
        )
        entity.metadata["recent_actions"] = recent[-8:]
        episode = Episode(
            entity_id=entity.id,
            episode_type=EpisodeType.ACTION_RESULT,
            tick=tick,
            x=entity.x,
            y=entity.y,
            summary=(
                f"{action.action_type.value.lower()} {outcome} while pursuing "
                f"{goal.goal_type.value.lower()}."
            ),
            importance=min(1.0, 0.35 + goal.utility_score * 0.4),
            details={
                "goal_id": str(goal.id),
                "action_id": str(action.id),
                "action_type": action.action_type.value,
                "succeeded": succeeded,
                "result": action.result,
                "failure_reason": action.failure_reason,
            },
        )
        world.episodes.setdefault(str(entity.id), []).append(episode)

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
