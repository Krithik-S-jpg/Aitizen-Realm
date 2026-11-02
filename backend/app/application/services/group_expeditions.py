"""Short, supply-checked overland expeditions. No teleportation or map reveal."""
from uuid import uuid4

from app.application.services.communication_service import CommunicationService
from app.application.services.memory_service import MemoryService
from app.application.services.diet import foods
from app.domain.models.entity import EntityKind
from app.domain.models.navigation import MovementStatus
from app.domain.models.memory import EpisodeType

FINISHED = {"completed", "aborted", "rescued"}


def provisions(world, citizen):
    inventory = world.inventories[str(citizen.id)]
    return sum(inventory.items.get(food, 0) for food in foods(citizen))


def ready(world, citizen, tick):
    from app.application.services.family_service import needs_light_duties
    if needs_light_duties(citizen):
        return False
    from app.application.services.family_service import adult
    if not adult(citizen):
        return False
    n = citizen.needs
    return (citizen.active and citizen.kind == EntityKind.AGENT and "autonomous" in citizen.tags
            and n and n.health >= 85 and n.energy >= 85 and n.hunger < 30 and n.thirst < 25
            and provisions(world, citizen) >= 2 and not citizen.metadata.get("group_expedition")
            and tick >= citizen.metadata.get("next_group_expedition", 0)
            and str(citizen.id) not in world.active_actions
            and not any(citizen.metadata.get(k) for k in ("community_task", "in_cave", "dive_trip", "aboard", "underwater"))
            and citizen.metadata.get("state") != "sleep")


def finish(world, trip, members, tick, phase, reason):
    trip.update(phase=phase, reason=reason, finished_tick=tick)
    for actor in members:
        action = world.actions.get(world.active_actions.get(str(actor.id), ""))
        if action and action.target.get("expedition_id") == trip["id"]:
            from app.domain.models.cognition import TaskStatus
            action.status = TaskStatus.FAILED
            action.failure_reason = reason
            action.completed_at_tick = tick
            goal = world.goals[str(action.goal_id)]
            goal.status = TaskStatus.FAILED
            goal.completed_at_tick = tick
            resource = world.resources.get(str(action.target.get("resource_id", "")))
            if resource and resource.reserved_by == str(actor.id):
                resource.release(str(actor.id))
            world.active_actions.pop(str(actor.id), None)
            world.active_goals.pop(str(actor.id), None)
        plan = world.movement_plans.get(str(actor.id))
        if plan and plan.status == MovementStatus.MOVING:
            plan.status = MovementStatus.CANCELLED
        from app.application.services.interior_rescue import release
        release(world, actor, tick)
        actor.metadata.pop("group_expedition", None)
        actor.metadata.pop("carried_by", None)
        actor.metadata.pop("carrying_casualty", None)
        actor.metadata.update(next_group_expedition=tick + 240, state="idle")


def advance(decisions, world, tick, daylight):
    """Return controlled IDs so the normal AI cannot overwrite expedition routes."""
    controlled = set()
    chat = CommunicationService(decisions._repository, MemoryService(decisions._repository))
    for trip in list(world.expeditions.values()):
        if trip["phase"] in FINISHED:
            continue
        if trip.get("last_advanced_tick") == tick:
            controlled.update(trip["members"])
            continue
        trip["last_advanced_tick"] = tick
        members = [world.entities[k] for k in trip["members"] if k in world.entities]
        if len(members) == 2:
            from app.application.services.expedition_rescue import retrieve
            try:
                if retrieve(decisions, world, trip, members, tick):
                    if trip["phase"] == "rescued":
                        finish(world, trip, members, tick, "rescued", trip["reason"])
                    else:
                        controlled.update(trip["members"])
                    continue
            except ValueError as error:
                finish(world, trip, members, tick, "aborted", str(error))
                continue
        if len(members) != 2 or any(not e.active for e in members):
            finish(world, trip, members, tick, "aborted", "A companion is unavailable")
            continue
        if trip["phase"] not in {"preparing", "cave_exploring", "boat_exploring"} and any(str(e.id) in world.active_actions or e.metadata.get("dive_trip") or e.metadata.get("in_cave") or e.metadata.get("aboard") for e in members):
            finish(world, trip, members, tick, "aborted", "Interrupted by another activity")
            continue
        for e in members:
            decisions._perception.observe(e.id, tick)
        if trip["phase"] in {"cave_exploring", "boat_exploring"}:
            if tick-trip.get("departed_tick", trip["started_tick"]) > 80:
                finish(world, trip, members, tick, "aborted", "Party travel timed out; individual return routines resumed")
                continue
            from app.application.services.expedition_routes import explore
            try:
                if explore(decisions, world, trip, members, tick):
                    controlled.update(trip["members"])
                    continue
            except ValueError as error:
                finish(world, trip, members, tick, "aborted", str(error))
                continue
        # Real first aid only: a nearby companion consumes their own carried fiber.
        for patient, helper in ((members[0], members[1]), (members[1], members[0])):
            if patient.needs.health < 70 and helper.distance_squared_to(patient.x, patient.y) <= 2 and not trip.get("first_aid"):
                inventory = world.inventories[str(helper.id)]
                if inventory.items.get("fiber", 0) >= 1:
                    inventory.consume({"fiber": 1})
                    patient.needs.health = min(70, patient.needs.health + 5)
                    trip["first_aid"] = {"helper": str(helper.id), "patient": str(patient.id), "tick": tick}
        if any(e.needs.critical or decisions._threats(world, e) for e in members):
            finish(world, trip, members, tick, "aborted", "Immediate survival emergency; individual safety AI resumed")
            continue
        if trip["phase"] == "planning":
            from app.application.services.expedition_planner import planner
            from app.core.config import settings
            choice = planner.choose(world, trip, tick, settings.OLLAMA_MODEL)
            if choice is None:
                controlled.update(trip["members"])
                continue
            index, reason, source = choice
            trip.update(trip["options"][index])
            trip.update(phase="preparing", reason=reason, planner=source)
        if trip["phase"] == "preparing":
            from app.application.services.expedition_equipment import prepare
            try:
                if trip.get("equipment_required") and not prepare(decisions, world, trip, members, tick):
                    if tick-trip["started_tick"] > 48 or not daylight:
                        raise ValueError("Preparation interrupted: daylight or time budget exhausted")
                    controlled.update(trip["members"])
                    continue
            except ValueError as error:
                for e in members:
                    active = decisions._lifecycle.active(e.id)
                    if active and active[1].target.get("expedition_id") == trip["id"]:
                        decisions._lifecycle.fail(*active, tick, str(error))
                finish(world, trip, members, tick, "aborted", str(error))
                continue
            trip.update(phase="outbound", departed_tick=tick)
        from app.application.services.expedition_routes import explore
        try:
            if explore(decisions, world, trip, members, tick):
                controlled.update(trip["members"])
                continue
        except ValueError as error:
            finish(world, trip, members, tick, "aborted", str(error))
            continue
        from app.application.services.expedition_camping import advance as camp
        if camp(decisions, world, trip, members, tick, daylight):
            controlled.update(trip["members"])
            continue
        if trip["phase"] == "outbound" and ((trip.get("kind") != "multi_day" and (not daylight or tick-trip.get("departed_tick", trip["started_tick"]) >= 10)) or any(
                e.needs.hunger > 45 or e.needs.thirst > 40 or e.needs.energy < 65 or e.needs.health < 85 for e in members)):
            trip.update(phase="returning", reason="Return before darkness or depleted reserves")
        if members[0].distance_squared_to(members[1].x, members[1].y) > 36:
            trip.update(phase="returning", reason="Companions separated; regroup at departure point")
        if trip["phase"] == "outbound" and all((e.x, e.y) == tuple(trip["targets"][str(e.id)]) for e in members):
            trip.update(phase="returning", reason="Reached survey destination")
        if tick-trip.get("departed_tick", trip["started_tick"]) > max(80, trip.get("day_ticks", 24) * 3):
            finish(world, trip, members, tick, "aborted", "Travel timed out; survival AI resumed")
            continue
        for e in members:
            knowledge = world.entity_knowledge[str(e.id)]
            found = [k for k in knowledge.resources if k not in trip["known_before"][str(e.id)]]
            trip["discoveries"][str(e.id)] = found[:25]
            if e.needs.hunger >= 35:
                item = next((f for f in foods(e) if world.inventories[str(e.id)].items.get(f, 0) >= 1), None)
                if item:
                    decisions._needs.eat(e.id, 1, item)
            target = trip["targets" if trip["phase"] == "outbound" else "origins"][str(e.id)]
            if (e.x, e.y) != tuple(target):
                plan = world.movement_plans.get(str(e.id))
                if not plan or plan.status != MovementStatus.MOVING or (plan.destination_x, plan.destination_y) != tuple(target):
                    try:
                        decisions._navigation.plan(e.id, *target, tick)
                    except ValueError:
                        finish(world, trip, members, tick, "aborted", "Known route no longer reachable")
                        break
            e.metadata.update(state="move", last_decision_reason=f"Expedition {trip['phase']}: {trip['reason']}")
        if trip["phase"] in FINISHED:
            continue
        if trip["phase"] == "returning" and all((e.x, e.y) == tuple(trip["origins"][str(e.id)]) for e in members):
            trip["reports"] = []
            for e in members:
                found = trip["discoveries"][str(e.id)]
                listeners = [p for p in world.entities.values() if str(p.id) not in trip["members"] and chat._available(p)
                             and e.distance_squared_to(p.x, p.y) <= chat.MAX_RANGE**2]
                for listener in listeners[:3]:
                    known_sites = list(world.entity_knowledge[str(e.id)].discoveries)[:5]
                    message = chat.send(e.id, listener.id,
                        f"We returned from {tuple(trip['destination'])}: {len(found)} new resource locations and {len(known_sites)} historical sites to discuss. Please check the evidence yourself.",
                        tick, {"resources": found[:20], "discoveries": known_sites})
                    trip["reports"].append(str(message.id))
                chat._memory.remember(e.id, EpisodeType.DISCOVERY, tick,
                    f"Returned from a shared survey with {len(found)} new resource locations.", .8,
                    {"expedition_id": trip["id"], "discoveries": found, "consequence": "Locations available to share"})
            finish(world, trip, members, tick, "completed", "Returned safely; reported to nearby citizens")
        else:
            controlled.update(trip["members"])
    if not daylight or tick % 24 != 6 or any(t["phase"] not in FINISHED for t in world.expeditions.values()):
        return controlled
    candidates = [e for e in world.entities.values() if ready(world, e, tick)]
    for leader in candidates:
        partners = [e for e in candidates if e.id != leader.id and leader.distance_squared_to(e.x, e.y) <= 4]
        if not partners or decisions._threats(world, leader):
            continue
        partner = partners[0]
        try:
            destination = decisions._exploration_target(world, leader)
            x, y = destination["x"], destination["y"]
            second = next(t for t in world.get_neighbors(x, y) if t.walkable
                          and f"{t.x},{t.y}" in world.entity_knowledge[str(partner.id)].tiles and (t.x, t.y) != (x, y))
            routes = [decisions._navigation._find_path(world, leader, x, y),
                      decisions._navigation._find_path(world, partner, second.x, second.y)]
            if any(not p or len(p) > 9 for p in routes):
                continue
        except (ValueError, StopIteration):
            continue
        members = [leader, partner]
        key = str(uuid4())
        trip = {"id": key, "phase": "preparing", "reason": "Survey the edge of our known terrain",
                "members": [str(e.id) for e in members], "destination": [x, y], "started_tick": tick,
                "origins": {str(e.id): [e.x, e.y] for e in members},
                "targets": {str(leader.id): [x, y], str(partner.id): [second.x, second.y]},
                "known_before": {str(e.id): list(world.entity_knowledge[str(e.id)].resources) for e in members},
                "discoveries": {str(e.id): [] for e in members}}
        world.expeditions[key] = trip
        from app.application.services.expedition_routes import itineraries
        from app.core.config import settings
        trip["options"] = itineraries(decisions, world, members, {
            "kind": "survey", "destination": trip["destination"], "targets": trip["targets"]})
        if destination.get("purpose") == "investigate":
            trip["options"].insert(0, {"kind": "investigation", "site_id": destination["site_id"],
                "destination": trip["destination"], "targets": trip["targets"]})
            trip["reason"] = "Investigate a personally known historical clue together"
        trip.update(trip["options"][0])
        trip.update(equipment_required=True, planner="utility")
        if settings.OLLAMA_MODEL and any(e.metadata.get("ai_mode") == "local_llm" for e in members):
            trip.update(phase="planning", reason="Local planner choosing a known itinerary")
        for e in members:
            e.metadata["group_expedition"] = key
            plan = world.movement_plans.get(str(e.id))
            if plan and plan.status == MovementStatus.MOVING:
                plan.status = MovementStatus.CANCELLED
        chat.send(leader.id, partner.id, f"Shall we survey near ({x}, {y}) together? We both have food. Let's make a short trip and return.", tick)
        chat.send(partner.id, leader.id, "I'll join you. We'll turn back if our needs or the route become unsafe.", tick)
        controlled.update(trip["members"])
        # Retain a bounded ledger; active trips are never pruned.
        for old in list(world.expeditions):
            if len(world.expeditions) <= 40:
                break
            if world.expeditions[old]["phase"] in FINISHED:
                del world.expeditions[old]
        break
    return controlled


def reports(world):
    return [{**t, "member_names": [world.entities[k].name if k in world.entities else "Unavailable" for k in t["members"]],
             "supplies": {k: dict(world.inventories[k].items) for k in t["members"] if k in world.inventories}}
            for t in world.expeditions.values()]
