"""Two-day surveys with an actual known waterside overnight stop."""
from app.application.services.diet import foods
from app.domain.models.calendar import get_calendar_control
from app.domain.models.navigation import MovementStatus


def offer(decisions, world, members):
    if any(sum(world.inventories[str(e.id)].items.get(f, 0) for f in foods(e)) < 8 for e in members):
        return None
    common = set(world.entity_knowledge[str(members[0].id)].tiles) & set(world.entity_knowledge[str(members[1].id)].tiles)
    for key in sorted(common):
        point = tuple(map(int, key.split(",")))
        tile = world.retrieve_tile(*point)
        if not tile or not tile.walkable or decisions._navigation._structure_blocks(world, *point):
            continue
        if not any(t.terrain.value in {"WATER", "WETLAND"} and f"{t.x},{t.y}" in common
                   for t in world.get_neighbors(*point)):
            continue
        if all((p := decisions._navigation._find_path(world, e, *point)) and len(p) <= 8 for e in members):
            return {"kind": "multi_day", "destination": list(point), "camp": list(point),
                    "targets": {str(e.id): list(point) for e in members},
                    "day_ticks": get_calendar_control().ticks_per_day}
    return None


def advance(decisions, world, trip, members, tick, daylight):
    if trip.get("kind") != "multi_day" or trip["phase"] not in {"outbound", "camping"}:
        return False
    if tick-trip["departed_tick"] > trip["day_ticks"] * 2:
        trip.update(phase="returning", reason="Two-day travel budget reached")
        for e in members:
            e.metadata["state"] = "idle"
        return False
    for e in members:
        if e.needs.hunger >= 30:
            item = next((f for f in foods(e) if world.inventories[str(e.id)].items.get(f, 0) >= 1), None)
            if item:
                decisions._needs.eat(e.id, 1, item)
        if e.needs.thirst >= 20:
            try:
                decisions._needs.drink_from_environment(e.id)
            except ValueError:
                pass
    if trip["phase"] == "outbound" and all([e.x, e.y] == trip["targets"][str(e.id)] for e in members):
        if trip.get("overnight_complete"):
            trip.update(phase="returning", reason="Second-day survey completed; return home")
            return False
        trip.update(phase="camping", reason="Rest at the known waterside camp until dawn")
    if trip["phase"] == "camping":
        if any(e.needs.hunger > 45 or e.needs.thirst > 40 or e.needs.health < 85 for e in members):
            trip.update(phase="returning", reason="Camp reserves insufficient; return before an emergency")
            for e in members:
                e.metadata["state"] = "idle"
            return False
        trip["night_observed"] = trip.get("night_observed", False) or not daylight
        for e in members:
            plan = world.movement_plans.get(str(e.id))
            if plan:
                plan.status = MovementStatus.CANCELLED
            decisions._needs.rest(e.id, 4)
            e.metadata.update(state="sleep" if not daylight else "rest", last_decision_reason=trip["reason"])
        if daylight and trip.get("night_observed"):
            trip["overnight_complete"] = True
            targets = {}
            try:
                for e in members:
                    target = decisions._exploration_target(world, e)
                    path = decisions._navigation._find_path(world, e, target["x"], target["y"])
                    if not path or len(path) > 8:
                        raise ValueError("Survey exceeds daylight reserve")
                    targets[str(e.id)] = [target["x"], target["y"]]
                trip.update(phase="outbound", targets=targets, reason="Second-day survey after overnight rest")
            except ValueError:
                trip.update(phase="returning", reason="No safe second-day route; returning from camp")
            for e in members:
                e.metadata["state"] = "idle"
        return True
    if tick-trip["departed_tick"] > trip["day_ticks"] * 2 or (trip.get("overnight_complete") and not daylight):
        trip.update(phase="returning", reason="Two-day travel budget reached")
    return False
