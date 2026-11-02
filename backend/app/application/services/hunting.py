"""Bounded, perception-limited hunting of real prey; no free meat rewards."""
from app.domain.models.cognition import ActionType, TaskStatus
from app.domain.models.entity import EntityKind
from app.application.services.animal_service import AnimalService

PREY = {"rabbit": 2.0, "deer": 8.0}


def target(decisions, world, citizen):
    from app.application.services.family_service import needs_light_duties
    if needs_light_duties(citizen):
        raise ValueError("Hunting is unavailable during pregnancy and recovery.")
    from app.application.services.family_service import adult
    if not adult(citizen):
        raise ValueError("Only adults can hunt.")
    needs = citizen.needs
    if citizen.diet == "vegetarian" or not needs or needs.hunger < 40 or needs.health < 75 or needs.energy < 55:
        raise ValueError("Hunting requires an omnivore with hunger, health and stamina.")
    known = world.entity_knowledge[str(citizen.id)].entities
    prey = next((e for e in sorted(world.entities.values(), key=lambda e: citizen.distance_squared_to(e.x, e.y))
                 if e.kind == EntityKind.ANIMAL and e.active and e.needs
                 and e.metadata.get("species") in PREY and str(e.id) in known
                 and citizen.distance_squared_to(e.x, e.y) <= citizen.perception_radius ** 2
                 and not any(world.actions[action_id].target.get("prey_id") == str(e.id)
                             for owner, action_id in world.active_actions.items()
                             if owner != str(citizen.id) and action_id in world.actions)), None)
    if prey is None:
        raise ValueError("No unclaimed prey is visible in known terrain.")
    inventory = world.inventories[str(citizen.id)]
    if inventory.items.get("hunting_spear", 0) < 1:
        if inventory.has({"wood": 3, "stone": 2, "fiber": 1}):
            return ActionType.CRAFT, {"item_type": "hunting_spear"}
        raise ValueError("Hunting requires a crafted spear.")
    if inventory.capacity - inventory.carried < 1:
        raise ValueError("Make room to carry meat first.")
    return ActionType.HUNT, {"prey_id": str(prey.id), "x": citizen.x, "y": citizen.y}


def advance(decisions, world, citizen, goal, action, tick):
    if action.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
        return
    try:
        if action.target.get("last_hunt_tick") == tick:
            return
        action.target["last_hunt_tick"] = tick
        prey = world.entities.get(action.target["prey_id"])
        if citizen.diet == "vegetarian" or not citizen.needs or citizen.needs.health < 60 or citizen.needs.energy < 25 or tick - action.created_at_tick > 24:
            raise ValueError("Hunt interrupted by diet, safety, fatigue or pursuit limit.")
        if not prey or not prey.active or not prey.needs or prey.kind != EntityKind.ANIMAL or prey.metadata.get("species") not in PREY or citizen.distance_squared_to(prey.x, prey.y) > citizen.perception_radius ** 2:
            raise ValueError("Prey is no longer visible or available.")
        if world.inventories[str(citizen.id)].items.get("hunting_spear", 0) < 1:
            raise ValueError("Hunting tool is missing.")
        if citizen.distance_squared_to(prey.x, prey.y) > 2:
            for tile in sorted(world.get_neighbors(prey.x, prey.y, include_diagonals=True), key=lambda t: citizen.distance_squared_to(t.x, t.y)):
                if not tile.walkable:
                    continue
                try:
                    decisions._navigation.plan(citizen.id, tile.x, tile.y, tick)
                    citizen.metadata["state"] = "move"
                    return
                except ValueError:
                    continue
            raise ValueError("No known route reaches the prey.")
        citizen.metadata["state"] = "hunt"
        action.work_required = 100
        action.progress = min(100, action.progress + 35)
        if str(citizen.id) in world.movement_plans:
            decisions._navigation.cancel(citizen.id)
        citizen.needs.energy = max(0, citizen.needs.energy - 3)
        prey.needs.health = max(0, prey.needs.health - 35)
        prey.metadata.update(state="flee", hunted_by=str(citizen.id))
        if prey.metadata.get("species") == "deer":
            citizen.needs.health = max(0, citizen.needs.health - 2)
        citizen.skills["hunting"] = min(100, citizen.skills.get("hunting", 0) + .5)
        if prey.needs.health <= 0:
            AnimalService(decisions._repository)._die(world, prey, tick, "citizen_hunt", PREY[prey.metadata["species"]])
            decisions._perception.observe(citizen.id, tick)
            decisions._lifecycle.complete(goal, action, tick, {"hunted": str(prey.id), "remains_at": [prey.x, prey.y]})
            citizen.metadata["state"] = "idle"
    except (KeyError, ValueError, LookupError) as error:
        if str(citizen.id) in world.movement_plans and not citizen.metadata.get("dive_trip"):
            decisions._navigation.cancel(citizen.id)
        decisions._lifecycle.fail(goal, action, tick, str(error))
