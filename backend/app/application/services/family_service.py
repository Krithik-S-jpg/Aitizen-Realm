"""Non-graphic, deterministic family lifecycle, stored entirely in checkpoints."""
from uuid import NAMESPACE_URL, uuid5
from app.domain.models.entity import Entity, EntityKind, EntityKnowledge, CitizenAvatar
from app.domain.models.inventory import Inventory
from app.domain.models.needs import NeedsState
from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.calendar import get_calendar_control


def age_days(actor):
    return float(actor.metadata.get("age_days", 18 * 365 + actor.id.int % (30 * 365)))


def stage(actor):
    age = age_days(actor) / 365
    return "infant" if age < 1 else "toddler" if age < 4 else "child" if age < 13 else "teen" if age < 18 else "adult" if age < 60 else "elder"


def adult(actor):
    return age_days(actor) >= 18 * 365


def pregnancy_status(actor):
    """Game-clock progress, not a medical prediction; also supports old saves."""
    pregnancy = actor.metadata.get("pregnancy")
    recovery = max(0.0, actor.metadata.get("recovery_until_age", 0) - age_days(actor))
    if not isinstance(pregnancy, dict):
        return {"phase": "recovering" if recovery else "none", "recovery_days": recovery}
    due = float(pregnancy["due_age_days"])
    start = float(pregnancy.get("started_age_days", due - 280))
    progress = max(0.0, min(1.0, (age_days(actor)-start) / max(1, due-start)))
    needs = actor.needs
    warnings = []
    if needs:
        if needs.hunger > 50: warnings.append("Needs food")
        if needs.thirst > 50: warnings.append("Needs water")
        if needs.energy < 50: warnings.append("Needs rest")
        if needs.health < 70: warnings.append("Needs help")
    return {"phase": "birth_due" if progress >= 1 else "pregnant", "progress": progress,
            "trimester": min(3, int(progress*3)+1), "days_remaining": max(0, due-age_days(actor)),
            "warnings": warnings, "recovery_days": recovery}


def needs_light_duties(actor):
    return bool(actor.metadata.get("pregnancy")) or age_days(actor) < actor.metadata.get("recovery_until_age", 0)


def age_tick(actor, tick):
    control = get_calendar_control()
    last = actor.metadata.get("age_last_tick", max(0, tick-1))
    if tick <= last:
        return
    actor.metadata["age_days"] = age_days(actor) + (tick-last) * control.biological_days_per_day / control.ticks_per_day
    actor.metadata.update(age_last_tick=tick, life_stage=stage(actor))
    if adult(actor) and actor.metadata.get("parent_ids"):
        actor.tags.add("autonomous")
    if age_days(actor) >= actor.metadata.get("maximum_age_days", 80 * 365):
        actor.active = False
        actor.metadata.update(state="dead", death_tick=tick, death_cause="old_age")


def home_for(world, actor):
    return next((h for h in world.structures.values() if h.completed and h.bed_capacity > 0 and str(actor.id) in h.resident_ids), None)


def related(a, b, world):
    def ancestors(actor):
        found = set()
        pending = list(actor.metadata.get("parent_ids", []))
        while pending:
            key = str(pending.pop())
            if key in found:
                continue
            found.add(key)
            parent = world.entities.get(key)
            if parent:
                pending.extend(parent.metadata.get("parent_ids", []))
        return found
    ap, bp = ancestors(a), ancestors(b)
    return str(a.id) in bp or str(b.id) in ap or bool(ap & bp)


def record(world, actor, tick, text):
    episodes = world.episodes.setdefault(str(actor.id), [])
    episodes.append(Episode(entity_id=actor.id, episode_type=EpisodeType.COMMUNICATION,
                            tick=tick, x=actor.x, y=actor.y, summary=text, importance=1))
    del episodes[:-200]


def advance(world, tick):
    if world is None:
        return
    synchronize_infants(world)
    actors = [a for a in world.entities.values() if a.active and a.kind == EntityKind.AGENT]
    for a in actors:
        if a.metadata.get("family_last_tick", -1) >= tick:
            continue
        a.metadata["family_last_tick"] = tick
        if not adult(a):
            care(world, a, actors, tick)
            continue
        pregnancy = a.metadata.get("pregnancy")
        if pregnancy and a.needs:
            # Small game-balancing increments; duplicate ticks are guarded above.
            a.needs.hunger = min(100, a.needs.hunger + .03)
            a.needs.thirst = min(100, a.needs.thirst + .04)
            a.metadata["prenatal_status"] = pregnancy_status(a)
        if pregnancy and age_days(a) >= pregnancy["due_age_days"]:
            # Birth ID is fixed at conception, making replays/load idempotent.
            child_id = uuid5(NAMESPACE_URL, pregnancy["id"])
            key = str(child_id)
            if key not in world.entities:
                child = Entity(id=child_id, kind=EntityKind.AGENT, name=f"Child of {a.name}"[:80],
                               x=a.x, y=a.y, needs=NeedsState(), gender="female" if child_id.int % 2 else "male",
                               avatar_id=CitizenAvatar.JUNIPER if child_id.int % 2 else CitizenAvatar.ROWAN,
                               group_id=a.group_id, metadata={"age_days": 0, "age_last_tick": tick, "birth_tick": tick,
                               "life_stage": "infant", "parent_ids": [str(a.id), pregnancy["partner_id"]],
                               "guardian_id": str(a.id), "state": "rest"})
                world.entities[key] = child
                world.entity_knowledge[key] = EntityKnowledge(observer_id=child.id)
                world.inventories[key] = Inventory()
                world.episodes[key] = []
                home = home_for(world, a)
                if home:
                    home.resident_ids.append(key)
                record(world, a, tick, f"Welcomed {child.name} into the family.")
                record(world, child, tick, "Born into the household.")
            a.metadata.pop("pregnancy", None)
            a.metadata.pop("prenatal_status", None)
            a.metadata.update(recovery_until_age=age_days(a)+42, next_pregnancy_age=age_days(a)+730)
        if a.metadata.get("partner_id") or not a.metadata.get("wants_children", a.id.int % 3 == 0):
            continue
        home = home_for(world, a)
        if not home or a.distance_squared_to(home.x, home.y) > 4:
            continue
        for b in actors:
            if a.id == b.id or not adult(b) or related(a,b,world) or b.metadata.get("partner_id"):
                continue
            if not b.metadata.get("wants_children", b.id.int % 3 == 0) or str(b.id) not in home.resident_ids:
                continue
            bonds = [world.social_bonds.get(f"{a.id}:{b.id}"), world.social_bonds.get(f"{b.id}:{a.id}")]
            if not all(bond and bond.trust >= .65 and bond.familiarity >= .5 for bond in bonds):
                continue
            if a.distance_squared_to(b.x,b.y) > 2:
                continue
            a.metadata["partner_id"], b.metadata["partner_id"] = str(b.id), str(a.id)
            record(world,a,tick,f"Formed a partnership with {b.name}.")
            record(world,b,tick,f"Formed a partnership with {a.name}.")
            break
    for mother in actors:
        if not get_calendar_control().family_births_enabled:
            break
        if mother.gender != "female" or not adult(mother) or mother.metadata.get("pregnancy"):
            continue
        partner = world.entities.get(mother.metadata.get("partner_id", ""))
        if not partner or not partner.active or not adult(partner) or partner.gender != "male" or related(mother, partner, world):
            continue
        if not all(a.metadata.get("wants_children", a.id.int % 3 == 0) for a in (mother,partner)):
            continue
        if age_days(mother) < mother.metadata.get("next_pregnancy_age", 0) or age_days(mother) > 45*365:
            continue
        home = home_for(world,mother)
        if not home or str(partner.id) not in home.resident_ids or len(home.resident_ids) >= home.bed_capacity:
            continue
        if mother.distance_squared_to(partner.x,partner.y) > 2:
            continue
        if not all(a.needs and a.needs.health > 80 and a.needs.hunger < 35 and a.needs.thirst < 35 for a in (mother,partner)):
            continue
        reserves = sum(sum(world.inventories[str(a.id)].items.get(item,0) for item in ("food","fruit","cooked_fish","cooked_meat")) for a in (mother,partner))
        if reserves < 12:
            continue
        mother.metadata["pregnancy"] = {"id": f"family:{mother.id}:{tick}", "partner_id": str(partner.id), "due_age_days": age_days(mother)+280, "started_age_days": age_days(mother), "started_tick": tick}
        record(world,mother,tick,"Expecting a child; preparing food and a safe home.")


def care(world, child, actors, tick):
    home = home_for(world,child)
    guardians = [a for a in actors if adult(a) and a.needs and a.needs.health > 30
                 and (str(a.id) in child.metadata.get("parent_ids",[]) or (home and str(a.id) in home.resident_ids))]
    nearby = [a for a in guardians if a.distance_squared_to(child.x,child.y) <= 2]
    guardian = min(nearby, key=lambda a: str(a.id), default=None)
    child.metadata.update(life_stage=stage(child), state="play" if stage(child) != "infant" else "rest")
    if not guardian:
        assigned = min(guardians, key=lambda a: (a.distance_squared_to(child.x, child.y), str(a.id)), default=None)
        if assigned:
            child.metadata["guardian_id"] = str(assigned.id)
        child.metadata["care_status"] = "Waiting for a nearby guardian"
        return
    child.metadata.update(guardian_id=str(guardian.id), care_status="Supervised", last_care_tick=tick)
    pack = world.inventories[str(guardian.id)]
    if child.needs.hunger > 20:
        foods = ("food", "fruit") if child.diet == "vegetarian" else ("food", "fruit", "cooked_fish", "cooked_meat")
        food = next((item for item in foods if pack.items.get(item,0)>=1), None)
        if food:
            pack.consume({food:1})
            child.needs.eat(20)
            guardian.metadata["care_animation_until"] = tick+3
    if child.needs.thirst > 20 and pack.items.get("water", 0) >= 1:
        pack.consume({"water": 1})
        child.needs.drink(20)
        guardian.metadata["care_animation_until"] = tick+3
    child.needs.rest(1)
    if child.needs.thirst > 20 and any(t.terrain.value in {"WATER", "WETLAND"} for t in world.get_neighbors(child.x,child.y,include_diagonals=True)):
        child.needs.drink(20)
    if home and child.distance_squared_to(home.x,home.y) <= 2:
        child.needs.body_temperature_c += (37-child.needs.body_temperature_c)*.1
    if stage(child) in {"child", "teen"} and tick % 12 == 0:
        guardian.metadata["teaching_animation_until"] = tick+3
        for skill, level in guardian.skills.items():
            child.skills[skill] = max(child.skills.get(skill, 0), min(level, child.skills.get(skill,0)+.05))


def caregiving(decisions, world, actor, tick):
    """Interrupt optional work to reach a dependent, using normal navigation."""
    infant = world.entities.get(str(actor.metadata.get("carrying_infant", "")))
    if infant is not None:
        home = home_for(world, infant) or home_for(world, actor)
        if home is None:
            release_infant(actor, infant)
            return False
        if actor.distance_squared_to(home.x, home.y) <= 2:
            release_infant(actor, infant)
            actor.metadata["last_decision_reason"] = "Brought my infant safely home."
            return True
        return route_infant_home(decisions, world, actor, infant, home, tick)
    if not adult(actor) or not actor.needs or actor.needs.health < 40 or actor.needs.safety < 40 or actor.needs.hunger > 70 or actor.needs.thirst > 70:
        return False
    if age_days(actor) < actor.metadata.get("recovery_until_age", 0):
        if actor.needs.energy < 80:
            actor.needs.rest(1)
            actor.metadata.update(state="rest", last_decision_reason="Recovering after childbirth.")
            return True
    children = [c for c in world.entities.values() if c.active and c.kind == EntityKind.AGENT and not adult(c)
                and c.metadata.get("guardian_id") == str(actor.id) and c.needs
                and (c.needs.hunger > 20 or c.needs.thirst > 20 or stage(c) in {"infant", "toddler"})]
    if not children:
        return False
    child = min(children, key=lambda c: actor.distance_squared_to(c.x,c.y))
    home = home_for(world, child) or home_for(world, actor)
    if stage(child) == "infant" and home and child.distance_squared_to(home.x, home.y) > 2 and actor.distance_squared_to(child.x,child.y) <= 2 and not actor.metadata.get("carrying_casualty"):
        return route_infant_home(decisions, world, actor, child, home, tick)
    pack = world.inventories[str(actor.id)]
    foods = ("food", "fruit") if child.diet == "vegetarian" else ("food", "fruit", "cooked_fish", "cooked_meat")
    required = (["water"] if child.needs.thirst > 20 and pack.items.get("water", 0) < 1 else [])
    if child.needs.hunger > 20 and not any(pack.items.get(food, 0) >= 1 for food in foods):
        home = home_for(world, actor)
        if home:
            required += [next((food for food in foods if home.stockpile.items.get(food, 0) >= 1), "food")]
    home = home_for(world, actor)
    available = [item for item in required if home and home.stockpile.items.get(item, 0) >= 1]
    if available and pack.capacity - pack.carried >= 1:
        if actor.distance_squared_to(home.x, home.y) <= 2:
            for item in available:
                amount = min(2, home.stockpile.items[item], pack.capacity-pack.carried)
                if amount > 0:
                    pack.add(item, amount)
                    home.stockpile.consume({item: amount})
        else:
            current = decisions._lifecycle.active(actor.id)
            if current:
                decisions._lifecycle.fail(*current, tick, "Collect household supplies for a dependent")
            plan = world.movement_plans.get(str(actor.id))
            if not plan or plan.status.value != "MOVING":
                reached = False
                for tile in sorted(world.get_neighbors(home.x, home.y, include_diagonals=True), key=lambda tile: actor.distance_squared_to(tile.x, tile.y)):
                    try:
                        decisions._navigation.plan(actor.id, tile.x, tile.y, tick)
                        reached = True
                        break
                    except ValueError:
                        continue
                if not reached:
                    actor.metadata["care_status"] = "Household supplies unreachable"
                    return False
            actor.metadata.update(state="caregiving", last_decision_reason="Fetch real household food and water for my dependent.")
            return True
    if not any(pack.items.get(food,0)>=1 for food in ("food","fruit","cooked_fish","cooked_meat","water")) and stage(child) not in {"infant", "toddler"}:
        return False
    current = decisions._lifecycle.active(actor.id)
    if current:
        decisions._lifecycle.fail(*current,tick,"Paused optional work to care for a dependent")
    if actor.distance_squared_to(child.x,child.y) > 2:
        plan = world.movement_plans.get(str(actor.id))
        if not plan or plan.status.value != "MOVING":
            try:
                decisions._navigation.plan(actor.id,child.x,child.y,tick)
            except ValueError:
                return False
        actor.metadata.update(state="caregiving", last_decision_reason="Return to a dependent who needs care.")
    else:
        actor.metadata.update(state="caregiving", last_decision_reason="Stay beside and feed my dependent.")
    return True


def release_infant(carrier, infant):
    carrier.metadata.pop("carrying_infant", None)
    infant.metadata.pop("infant_carried_by", None)
    infant.metadata["care_status"] = "Resting after transport"


def synchronize_infants(world):
    """Saved reciprocal ownership; no teleport to a distant/new guardian."""
    for infant in world.entities.values():
        carrier_id = infant.metadata.get("infant_carried_by")
        if not carrier_id:
            continue
        carrier = world.entities.get(str(carrier_id))
        if carrier is None or not carrier.active or not infant.active or stage(infant) != "infant" or carrier.metadata.get("carrying_infant") != str(infant.id):
            infant.metadata.pop("infant_carried_by", None)
            if carrier and carrier.metadata.get("carrying_infant") == str(infant.id):
                carrier.metadata.pop("carrying_infant", None)
            infant.metadata["care_status"] = "Needs a guardian"
            continue
        infant.x, infant.y = carrier.x, carrier.y
        infant.metadata["care_status"] = "Carried safely home"


def route_infant_home(decisions, world, actor, infant, home, tick):
    """Use an actual known land route before claiming the infant."""
    from app.domain.models.navigation import MovementStatus
    if infant.metadata.get("infant_carried_by") not in (None, "", str(actor.id)):
        return False
    current = decisions._lifecycle.active(actor.id)
    if current:
        decisions._lifecycle.fail(*current, tick, "Escort infant home")
    plan = world.movement_plans.get(str(actor.id))
    if not plan or plan.status != MovementStatus.MOVING or (plan.destination_x-home.x)**2 + (plan.destination_y-home.y)**2 > 2:
        plan = None
        destinations = sorted(world.get_neighbors(home.x, home.y, include_diagonals=True), key=lambda tile: actor.distance_squared_to(tile.x, tile.y))
        for destination in destinations:
            try:
                plan = decisions._navigation.plan(actor.id, destination.x, destination.y, tick)
                break
            except ValueError:
                continue
        if plan is None:
            actor.metadata["last_decision_reason"] = "Cannot find a safe known route home for the infant."
            return True
    if any(not world.retrieve_tile(x, y) or not world.retrieve_tile(x, y).walkable for x, y in plan.path):
        plan.status = MovementStatus.CANCELLED
        actor.metadata["last_decision_reason"] = "Infant transport requires a dry land route."
        return True
    actor.metadata.update(carrying_infant=str(infant.id), state="caregiving")
    infant.metadata["infant_carried_by"] = str(actor.id)
    infant.x, infant.y = actor.x, actor.y
    return True
