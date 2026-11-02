"""Consistent live action, target and route details for both observer feeds."""

from app.domain.models.entity import Entity
from app.core.config import settings
from app.domain.models.world import World
from app.application.services.danger_memory import fear_at, sheltered, sleeping_home


def visual_identity(entity: Entity) -> str:
    """Resolve presentation without changing a citizen's saved appearance ID."""
    from app.application.services.family_service import stage
    life_stage = stage(entity)
    if life_stage == "infant":
        return "family_infant"
    if life_stage in {"toddler", "child", "teen", "elder"}:
        return "family_" + life_stage + ("_female" if entity.gender == "female" else "_male")
    return entity.avatar_id.value


def activity_details(world: World, entity: Entity) -> dict:
    """Expose authoritative plans, including routines without a work action."""
    key = str(entity.id)
    action = world.actions.get(world.active_actions.get(key, ""))
    goal = world.goals.get(world.active_goals.get(key, ""))
    plan = world.movement_plans.get(key)
    metadata = entity.metadata
    boat = world.entities.get(str(metadata.get("boat_id", "")))
    residence = sleeping_home(world, entity)
    state = str(metadata.get("state", "idle"))
    if metadata.get("in_cave"):
        state = "cave_explore"
    aquatic = bool(metadata.get("dive_trip") or metadata.get("aboard"))
    if aquatic:
        state = (
            ("dive_" + str(metadata.get("dive_phase", "explore")))
            if metadata.get("dive_trip")
            else "row"
            if plan and plan.status.value == "MOVING"
            else "aboard"
        )
    routine = aquatic or state in {"sleep", "seek_shelter", "socialize", "cave_explore", "deliver_supplies", "meet_for_meal", "shared_meal"}
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
        (
            metadata.get("last_decision_reason", "")
            if routine
            else goal.reason
            if goal is not None
            else ""
        )
        or metadata.get("behavior_reason")
        or metadata.get("blocked_reason")
        or metadata.get("last_decision_reason", "")
    )
    route = []
    from app.application.services.family_service import stage, pregnancy_status
    life_stage = stage(entity)
    visual_avatar = visual_identity(entity)
    if aquatic and plan is not None:
        target = {"x": plan.destination_x, "y": plan.destination_y}
    if plan is not None and plan.status.value == "MOVING":
        route = [[x, y] for x, y in plan.path[plan.next_step_index :]]
    return {
        "visual_avatar": visual_avatar,
        "life_stage": life_stage,
        "pregnancy_status": pregnancy_status(entity),
        "care_animation": metadata.get("care_animation_until", -1) >= metadata.get("family_last_tick", 0),
        "teaching_animation": metadata.get("teaching_animation_until", -1) >= metadata.get("family_last_tick", 0),
        "family": {"partner_id": metadata.get("partner_id"), "parent_ids": metadata.get("parent_ids", []),
                   "guardian_id": metadata.get("guardian_id"), "pregnancy": metadata.get("pregnancy"),
                   "care_status": metadata.get("care_status"), "age_days": metadata.get("age_days")},
        "gender": entity.gender,
        "carried_by": metadata.get("carried_by", ""),
        "infant_carried_by": metadata.get("infant_carried_by", ""),
        "carrying_infant": metadata.get("carrying_infant", ""),
        "carrying_casualty": metadata.get("carrying_casualty", ""),
        "carried_avatar": visual_identity(world.entities[str(metadata["carrying_casualty"])])
        if str(metadata.get("carrying_casualty", "")) in world.entities else "",
        "diet": entity.diet,
        "ai_mode": metadata.get(
            "ai_mode", "local_llm" if settings.LLM_CITIZEN_ID == key else "utility"
        ),
        "action": state
        if routine or action is None
        else action.action_type.value.lower(),
        "action_target": target,
        "decision_reason": reason,
        "decision_trace": metadata.get("decision_trace", []),
        "learning": {
            "ambition": metadata.get("ambition", {}),
            "known_dangers": list(metadata.get("learned_dangers", {}).values()),
            "last_outcome": metadata.get("last_learned_outcome", {}),
            "verified_report": metadata.get("last_verified_report", {}),
            "planner_status": metadata.get("llm_planner", {}).get("status", "Deterministic utility decisions"),
        },
        "route": route,
        "route_status": plan.status.value.lower() if plan is not None else "none",
        "indoors": sheltered(world, entity),
        "sleep_home_position": [residence.x, residence.y] if residence else None,
        "travel_mode": metadata.get("travel_mode", "walk"),
        "underwater": bool(metadata.get("underwater", False)),
        "oxygen": float(metadata.get("oxygen", 100)),
        "dive_phase": metadata.get("dive_phase", "none"),
        "boat": {
            "id": str(boat.id),
            "anchored": boat.metadata.get("anchored", True),
            "x": boat.x,
            "y": boat.y,
            "cargo": world.inventories[str(boat.id)].model_dump()
            if str(boat.id) in world.inventories
            else {},
        }
        if boat
        else None,
        "dive_origin": metadata.get("dive_origin"),
        "marine_discoveries": metadata.get("marine_discoveries", {}),
        "depth": world.retrieve_tile(entity.x, entity.y)
        .metadata.get("marine", {})
        .get("depth", 0)
        if metadata.get("underwater") and world.retrieve_tile(entity.x, entity.y)
        else 0,
        "fear": fear_at(
            entity, int(metadata.get("emotion_tick", metadata.get("decision_tick", 0)))
        ),
    }
