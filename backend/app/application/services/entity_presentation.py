"""Consistent live action, target and route details for both observer feeds."""

from app.domain.models.entity import Entity
from app.domain.models.world import World
from app.application.services.danger_memory import fear_at, sheltered


def activity_details(world: World, entity: Entity) -> dict:
    """Expose authoritative plans, including routines without a work action."""
    key = str(entity.id)
    action = world.actions.get(world.active_actions.get(key, ""))
    goal = world.goals.get(world.active_goals.get(key, ""))
    plan = world.movement_plans.get(key)
    metadata = entity.metadata
    state = str(metadata.get("state", "idle"))
    routine = state in {"sleep", "seek_shelter", "socialize"}
    target = dict(action.target) if action is not None and not routine else {}
    if not target and state in {"sleep", "seek_shelter"}:
        destination = metadata.get("night_destination")
        if isinstance(destination, list) and len(destination) == 2:
            target = {"x": destination[0], "y": destination[1]}
        home = world.structures.get(str(metadata.get("sleep_home_id", "")))
        if home is not None:
            target.update({"structure_id": str(home.id), "x": home.x, "y": home.y})
    if not target and isinstance(metadata.get("movement_target"), list):
        destination = metadata["movement_target"]
        if len(destination) == 2:
            target = {"x": destination[0], "y": destination[1]}
    reason = (
        metadata.get("last_decision_reason", "")
        if routine else goal.reason if goal is not None else ""
    ) or metadata.get("behavior_reason") or metadata.get("blocked_reason") or metadata.get("last_decision_reason", "")
    route = []
    if plan is not None and plan.status.value == "MOVING":
        route = [[x, y] for x, y in plan.path[plan.next_step_index:]]
    return {
        "action": state if routine or action is None else action.action_type.value.lower(),
        "action_target": target,
        "decision_reason": reason,
        "decision_trace": metadata.get("decision_trace", []),
        "route": route,
        "route_status": plan.status.value.lower() if plan is not None else "none",
        "indoors": sheltered(world, entity),
        "fear": fear_at(entity, int(metadata.get("emotion_tick", metadata.get("decision_tick", 0)))),
    }
