"""Gradual village upkeep and real reserve accounting, persisted with the world."""

from app.domain.models.calendar import calendar_at_tick
from app.domain.models.entity import EntityKind
from app.domain.models.navigation import MovementStatus

FOOD = ("food", "fruit", "meat", "cooked_meat", "mushroom", "raw_fish", "cooked_fish")


def record(group, tick, text):
    """Keep a bounded factual settlement story."""
    group.village_story.append({"tick": tick, "text": text})
    del group.village_story[:-40]


def advance_village(world, tick):
    """Apply daily wear and spoilage once, even after restoring a save."""
    if world is None:
        return
    calendar = calendar_at_tick(tick)
    agents = [e for e in world.entities.values() if e.active and e.kind == EntityKind.AGENT]
    for site in world.structures.values():
        if not site.completed or site.last_upkeep_day >= calendar.day:
            continue
        if site.last_upkeep_day == 0:
            site.last_upkeep_day = calendar.day
            continue
        site.last_upkeep_day = calendar.day
        inhabited = any(e.distance_squared_to(site.x, site.y) <= 144 for e in agents)
        storm_wear = 1.0 if calendar.weather_intensity >= .7 and calendar.wind_speed >= 10 else 0.0
        site.condition = max(0, site.condition - (.1 if inhabited else .5) - storm_wear)
    for group in world.groups.values():
        members = [e for e in agents if e.id in group.member_ids]
        project = group.community_project
        if project and project.get("status") in {"proposed", "agreed"}:
            target = world.structures.get(project["target"])
            if target is None or target.completed:
                project["status"] = "completed" if target else "cancelled"
                record(group, tick, "Community project " + project["status"] + ": " + project["title"])
        sites = [s for s in world.structures.values() if
                 (s.x-group.home_x)**2 + (s.y-group.home_y)**2 <= 144 and
                 min(world.groups.values(), key=lambda g: ((s.x-g.home_x)**2+(s.y-g.home_y)**2, str(g.id))).id == group.id]
        group.reserve_target = len(members) * (8 if calendar.season.value in {"AUTUMN", "WINTER"} else 4)
        edible = sum(inv.items.get(food, 0) for inv in
                     [world.inventories[str(e.id)] for e in members] + [s.stockpile for s in sites]
                     for food in FOOD if food != "raw_fish")
        for citizen in members:
            citizen.metadata["village_food_shortage"] = edible < group.reserve_target
        if group.last_village_day >= calendar.day:
            continue
        first_day = group.last_village_day == 0
        group.last_village_day = calendar.day
        spoiled = 0.0
        if not first_day:
            # Cool covered stockpiles preserve food better than carried supplies.
            inventories = [(world.inventories[str(e.id)], .03) for e in members]
            inventories += [(s.stockpile, .01) for s in sites]
            for inventory, rate in inventories:
                for food in FOOD:
                    amount = inventory.items.get(food, 0) * rate
                    if amount > 0:
                        inventory.consume({food: amount})
                        spoiled += amount
        beds = sum(s.bed_capacity for s in sites if s.completed)
        injured = sum(e.needs is not None and e.needs.health < 70 for e in members)
        record(group, tick, f"Day {calendar.day}: {len(members)} residents, {beds} beds; "
               f"food {max(0, edible-spoiled):.1f}/{group.reserve_target:.0f} reserve target; "
               f"{spoiled:.1f} food spoiled, {injured} citizens need recovery.")


def upkeep_action(decisions, world, citizen, tick, threats):
    """Idle citizens recover or repair nearby known structures using carried wood."""
    needs = citizen.needs
    if not needs or threats or needs.hunger >= 50 or needs.thirst >= 50:
        release_job(world, citizen)
        return False
    if needs.health < 70:
        release_job(world, citizen)
        decisions._needs.rest(citizen.id, 2)
        needs.health = min(70, needs.health + .5)
        citizen.metadata.update(state="rest", last_decision_reason="Recover from injury while food and water needs are satisfied.")
        return True
    inventory = world.inventories[str(citizen.id)]
    if needs.energy < 50:
        release_job(world, citizen)
        return False
    knowledge = world.entity_knowledge[str(citizen.id)]
    job = citizen.metadata.get("village_job")
    if job and tick >= job["expires"]:
        release_job(world, citizen)
        job = None
    claimed = {e.metadata["village_job"]["target"] for e in world.entities.values()
               if e.id != citizen.id and e.active and e.metadata.get("village_job", {}).get("expires", -1) > tick}
    if not job:
        patient = next((e for e in world.entities.values() if e.id != citizen.id and e.active
                        and e.kind == EntityKind.AGENT and e.needs and e.needs.health < 65
                        and str(e.id) in knowledge.entities and str(e.id) not in claimed
                        and citizen.distance_squared_to(e.x, e.y) <= 36
                        and e.metadata.get("next_first_aid_tick", 0) <= tick), None)
        if patient and inventory.items.get("fiber", 0) >= 1:
            job = {"kind": "first_aid", "target": str(patient.id), "expires": tick + 16}
        elif inventory.items.get("wood", 0) >= 1:
            site = next((s for s in sorted(world.structures.values(), key=lambda s: citizen.distance_squared_to(s.x, s.y))
                         if s.completed and s.condition < 90 and str(s.id) in knowledge.structures
                         and str(s.id) not in claimed), None)
            if site:
                job = {"kind": "repair", "target": str(site.id), "expires": tick + 24}
        if job:
            citizen.metadata["village_job"] = job
    if not job:
        return False
    target = (world.entities if job["kind"] == "first_aid" else world.structures).get(job["target"])
    material = "fiber" if job["kind"] == "first_aid" else "wood"
    if target is None or inventory.items.get(material, 0) < 1:
        release_job(world, citizen)
        return False
    if job["kind"] == "first_aid" and (not target.active or not target.needs or target.needs.health >= 65
            or target.metadata.get("state") == "sleep" or any(target.metadata.get(k) for k in ("in_cave", "dive_trip", "aboard"))):
        release_job(world, citizen)
        return False
    if job["kind"] == "repair" and (not target.completed or target.condition >= 90):
        release_job(world, citizen)
        return False
    citizen.metadata["last_decision_reason"] = "Deliver first aid to an injured neighbour." if material == "fiber" else "Travel to a known worn building with repair supplies."
    if citizen.distance_squared_to(target.x, target.y) > 2:
        plan = world.movement_plans.get(str(citizen.id))
        if job.get("owns_route") and plan and plan.status == MovementStatus.MOVING:
            citizen.metadata["state"] = "move"
            return True
        for tile in sorted(world.get_neighbors(target.x, target.y, include_diagonals=True), key=lambda t: citizen.distance_squared_to(t.x, t.y)):
            if not tile.walkable or any(e.active and e.id != citizen.id and (e.x, e.y) == (tile.x, tile.y) for e in world.entities.values()):
                continue
            try:
                decisions._navigation.plan(citizen.id, tile.x, tile.y, tick)
                job["owns_route"] = True
                citizen.metadata["state"] = "move"
                return True
            except ValueError:
                continue
        release_job(world, citizen)
        return False
    if material == "fiber":
        inventory.consume({"fiber": 1})
        target.needs.health = min(70, target.needs.health + 5)
        target.metadata["next_first_aid_tick"] = tick + 24
        citizen.metadata.update(state="craft", last_decision_reason=f"Used one fiber to bandage {target.name}.")
        group = world.groups.get(str(citizen.group_id))
        if group:
            record(group, tick, f"{citizen.name} gave first aid to {target.name}.")
        release_job(world, citizen)
        return True
    site = target
    inventory.consume({"wood": 1})
    site.condition = min(100, site.condition + 10)
    citizen.metadata.update(state="craft", last_decision_reason="Used one carried wood to maintain a worn building.")
    group = world.groups.get(str(citizen.group_id))
    if group:
        record(group, tick, f"{citizen.name} repaired the {site.structure_type.value.lower()} to {site.condition:.0f}% condition.")
    release_job(world, citizen)
    return True


def release_job(world, citizen):
    """Release a claim without cancelling another system's movement."""
    job = citizen.metadata.pop("village_job", None)
    plan = world.movement_plans.get(str(citizen.id))
    if job and job.get("owns_route") and plan and plan.status == MovementStatus.MOVING:
        plan.status = MovementStatus.CANCELLED


def discuss_project(chat, world, speaker, listener, tick):
    """Neighbours endorse a real known construction project; a majority agrees."""
    from app.application.services.community_routines import safe
    if not speaker.group_id or speaker.group_id != listener.group_id or not all(safe(e, tick) for e in (speaker, listener)):
        return False
    group = world.groups.get(str(speaker.group_id))
    if group is None:
        return False
    project = group.community_project
    if not project or project.get("status") in {"completed", "cancelled"}:
        known = world.entity_knowledge[str(speaker.id)].structures
        site = next((s for s in world.structures.values() if not s.completed and str(s.id) in known
                     and speaker.distance_squared_to(s.x, s.y) <= 36), None)
        if site is None:
            return False
        project = {"target": str(site.id), "title": "Finish the " + site.structure_type.value.lower(),
                   "status": "proposed", "votes": [str(speaker.id)], "created_tick": tick}
        group.community_project = project
        record(group, tick, speaker.name + " proposed: " + project["title"])
    if str(listener.id) in project["votes"] or project["status"] != "proposed":
        return False
    if project["target"] not in world.entity_knowledge[str(speaker.id)].structures:
        return False
    chat.send(speaker.id, listener.id, f"Shall we work together to {project['title'].lower()}?", tick,
              {"structures": [project["target"]]})
    chat.send(listener.id, speaker.id, "I agree. Let's finish that project when our immediate needs are met.", tick)
    project["votes"].append(str(listener.id))
    active = {str(e.id) for e in world.entities.values() if e.active and e.id in group.member_ids}
    if len(active.intersection(project["votes"])) >= len(active) // 2 + 1:
        project["status"] = "agreed"
        record(group, tick, "A majority agreed: " + project["title"])
    return True
