"""Bounded social commitments, using real inventories and known walkable routes.

Tasks live in entity metadata so checkpoints preserve them. No actor is moved or
fed by dialogue; the normal navigation and needs services perform those actions.
"""

from app.domain.models.navigation import MovementStatus
from app.domain.models.structure import StructureType
from app.domain.models.memory import EpisodeType
from app.application.services.diet import foods

FOODS = ("cooked_fish", "food", "fruit", "meat", "mushroom")


def safe(actor, tick):
    needs = actor.needs
    return bool(needs and needs.health >= 60 and needs.hunger < 75
                and needs.thirst < 65 and needs.energy > 30
                and actor.metadata.get("wildlife_warning", {}).get("expires", -1) < tick)


def finish(world, actor, status, tick):
    task = actor.metadata.pop("community_task", None)
    if task:
        actor.metadata["last_community_task"] = {**task, "status": status, "finished_tick": tick}
        plan = world.movement_plans.get(str(actor.id))
        if task.get("owns_route") and plan and plan.status == MovementStatus.MOVING:
            plan.status = MovementStatus.CANCELLED
    if actor.metadata.get("state") in {"deliver_supplies", "meet_for_meal", "shared_meal"}:
        actor.metadata["state"] = "idle"


def complete_deliveries(service, world, tick):
    for actor in world.entities.values():
        task = actor.metadata.get("community_task")
        if not task:
            continue
        if not service._available(actor) or tick >= task["expires"] or not safe(actor, tick):
            finish(world, actor, "Interrupted by survival needs or expiry", tick)
            continue
        if task["kind"] != "delivery":
            continue
        if tick <= task["created_tick"]:
            continue
        recipient = world.entities.get(task["recipient_id"])
        if not recipient or not service._available(recipient):
            finish(world, actor, "Recipient unavailable", tick)
            continue
        if actor.distance_squared_to(recipient.x, recipient.y) > 2:
            continue
        try:
            service.give(actor.id, recipient.id, task["item"], task["amount"], tick)
            service.send(recipient.id, actor.id, "Thank you. You brought the supplies you promised.", tick)
            finish(world, actor, "Delivered", tick)
        except ValueError as error:
            finish(world, actor, str(error), tick)


def converse(service, world, a, b, tick):
    # Spoken warnings retain their original expiry and provenance, not omniscience.
    for witness, listener in ((a, b), (b, a)):
        warning = witness.metadata.get("wildlife_warning", {})
        warning_key = str([warning.get("x"), warning.get("y"), warning.get("expires")])
        if warning.get("expires", -1) >= tick and listener.metadata.get("heard_warning") != warning_key:
            service.send(witness.id, listener.id,
                         (f"{'I was attacked by' if warning.get('witness_id') == str(witness.id) and warning.get('experience') == 'attacked' else 'I learned about an attack by'} "
                          f"a {warning.get('species', 'dangerous animal')} near ({warning['x']}, {warning['y']}). Don't approach it; use another route.")[:240]
                         if warning.get("species") else f"Danger near ({warning['x']}, {warning['y']}). Stay away and find safety!", tick)
            listener.metadata.update(wildlife_warning=dict(warning), heard_warning=warning_key)
            from app.application.services.adaptive_learning import remember_danger
            remember_danger(listener, warning, witness.id)
            service._memory.remember(listener.id, EpisodeType.COMMUNICATION, tick,
                                     f"{witness.name} warned me about nearby danger.", .85,
                                     {"consequence": "Avoid the reported location", "warning": dict(warning),
                                      "event_id": warning.get("event_id"), "source_id": str(witness.id)}, [witness.id])
            service.send(listener.id, witness.id, "Thanks for warning me. I'll avoid that area while the report is recent.", tick)
            return True
    for donor, receiver in ((a, b), (b, a)):
        if donor.metadata.get("community_task") or not safe(donor, tick):
            continue
        source = world.inventories.get(str(donor.id))
        destination = world.inventories.get(str(receiver.id))
        if not source or not destination or destination.capacity - destination.carried < 2:
            continue
        if receiver.needs and receiver.needs.hunger >= 45 and donor.needs.hunger < 40:
            food = next((item for item in foods(receiver) if source.items.get(item, 0) >= 4), None)
            if food and not any(e.metadata.get("community_task", {}).get("recipient_id") == str(receiver.id)
                                for e in world.entities.values()):
                service.send(receiver.id, donor.id, "I am hungry. Could you bring me some food?", tick)
                service.send(donor.id, receiver.id, "Yes. I have some to spare; I will bring it over.", tick)
                donor.metadata["community_task"] = {
                    "kind": "delivery", "recipient_id": str(receiver.id), "item": food,
                    "amount": 2, "created_tick": tick, "expires": tick + 16}
                return True
    if any(e.metadata.get("community_task") for e in (a, b)):
        return True
    from app.application.services.village_service import discuss_project
    if discuss_project(service, world, a, b, tick):
        return True
    if a.distance_squared_to(b.x, b.y) <= 2 and safe(a, tick) and safe(b, tick):
        def deficits(actor):
            inventory = world.inventories[str(actor.id)]
            known = world.entity_knowledge[str(actor.id)].structures
            return {item for site in world.structures.values() if str(site.id) in known
                    and not site.completed for item, amount in site.missing_materials.items()
                    if inventory.items.get(item, 0) < amount}
        needs_a, needs_b = deficits(a), deficits(b)
        source_a, source_b = world.inventories[str(a.id)], world.inventories[str(b.id)]
        offered = next((item for item in sorted(needs_b - needs_a) if source_a.items.get(item, 0) >= 2), None)
        requested = next((item for item in sorted(needs_a - needs_b) if source_b.items.get(item, 0) >= 2), None)
        if offered and requested:
            service.barter(a.id, b.id, offered, requested, tick)
            return True
    # Only invite idle, safe citizens with their own real food and a known fire.
    if all(safe(e, tick) and str(e.id) not in world.active_actions
           and e.needs.hunger >= 10
           and tick >= e.metadata.get("next_shared_meal", 0)
           and any(world.inventories[str(e.id)].items.get(food, 0) >= 1 for food in foods(e))
           for e in (a, b)):
        fire = next((s for s in world.structures.values()
                     if s.completed and s.structure_type == StructureType.CAMPFIRE and s.fuel > 0
                     and all(e.distance_squared_to(s.x, s.y) <= 36
                             and str(s.id) in world.entity_knowledge[str(e.id)].structures for e in (a, b))), None)
        if fire:
            service.send(a.id, b.id, "Let's eat together by the campfire.", tick)
            service.send(b.id, a.id, "Good idea. I have food with me; I'll meet you there.", tick)
            for actor, partner in ((a, b), (b, a)):
                actor.metadata["community_task"] = {"kind": "meal", "fire_id": str(fire.id),
                    "partner_id": str(partner.id), "expires": tick + 20, "created_tick": tick}
                actor.metadata["next_shared_meal"] = tick + 96
            return True
    # A concrete construction request shares only a site the speaker remembers.
    for speaker, listener in ((a, b), (b, a)):
        knowledge = world.entity_knowledge[str(speaker.id)]
        site = next((s for s in world.structures.values() if not s.completed
                     and str(s.id) in knowledge.structures
                     and speaker.distance_squared_to(s.x, s.y) <= 36), None)
        if site and listener.metadata.get("help_site") != str(site.id):
            missing = ", ".join(f"{amount:g} {item}" for item, amount in site.missing_materials.items())
            service.send(speaker.id, listener.id,
                         (f"Can you help at the building near ({site.x}, {site.y})? "
                          + (f"It still needs {missing}." if missing else "The materials are ready for building."))[:240],
                         tick, {"structures": [str(site.id)]})
            listener.metadata["help_site"] = str(site.id)
            service.send(listener.id, speaker.id, "I know the site now. I'll check for useful work when my needs are met.", tick)
            return True
    return False


def advance_routine(decisions, world, actor, tick, threats):
    task = actor.metadata.get("community_task")
    if not task:
        return False
    if threats or not safe(actor, tick) or tick >= task["expires"]:
        finish(world, actor, "Interrupted by survival needs or expiry", tick)
        return False
    if task["kind"] == "delivery":
        target = world.entities.get(task["recipient_id"])
        if not target or not target.active:
            finish(world, actor, "Recipient unavailable", tick)
            return False
        actor.metadata.update(state="deliver_supplies", last_decision_reason="Bring promised supplies to a nearby citizen.")
    else:
        target = world.structures.get(task["fire_id"])
        partner = world.entities.get(task["partner_id"])
        if not target or not target.completed or target.fuel <= 0 or not partner or not partner.active:
            finish(world, actor, "Meal location or companion unavailable", tick)
            return False
        partner_task = partner.metadata.get("community_task", {})
        recent_meal = partner.metadata.get("last_community_task", {})
        joining = partner_task.get("kind") == "meal" and partner_task.get("fire_id") == task["fire_id"]
        just_finished = (recent_meal.get("status") == "Shared meal completed"
                         and recent_meal.get("fire_id") == task["fire_id"]
                         and tick - recent_meal.get("finished_tick", -100) <= 3)
        if not joining and not just_finished:
            finish(world, actor, "Companion left the shared meal", tick)
            return False
        actor.metadata.update(state="meet_for_meal", last_decision_reason="Meet a companion at a lit campfire with carried food.")
        if actor.distance_squared_to(target.x, target.y) <= 2 and partner.distance_squared_to(target.x, target.y) <= 2:
            if "ate_tick" not in task:
                food = next((f for f in foods(actor) if world.inventories[str(actor.id)].items.get(f, 0) >= 1), None)
                if not food:
                    finish(world, actor, "No carried food remains", tick)
                    return False
                decisions._needs.eat(actor.id, 1, food)
                task["ate_tick"] = tick
                actor.metadata["meal_animation_until"] = tick + 3
            actor.metadata["state"] = "shared_meal"
            if tick - task["ate_tick"] >= 3:
                finish(world, actor, "Shared meal completed", tick)
            return True
    if actor.distance_squared_to(target.x, target.y) <= 2:
        return True
    plan = world.movement_plans.get(str(actor.id))
    if task.get("owns_route") and plan and plan.status == MovementStatus.MOVING:
        return True
    candidates = sorted(world.get_neighbors(target.x, target.y, include_diagonals=True),
                        key=lambda tile: actor.distance_squared_to(tile.x, tile.y))
    for tile in candidates:
        if not tile.walkable or any(e.active and e.id != actor.id and (e.x, e.y) == (tile.x, tile.y) for e in world.entities.values()):
            continue
        try:
            decisions._navigation.plan(actor.id, tile.x, tile.y, tick)
            task["owns_route"] = True
            return True
        except ValueError:
            continue
    finish(world, actor, "No known safe route to companion", tick)
    return False
