"""Expedition preparation uses the same reserved jobs as ordinary work."""
from uuid import UUID

from app.domain.models.cognition import ActionType, GoalType
from app.domain.models.resource import ResourceType


def prepare(decisions, world, trip, members, tick):
    """Return True only when every member carries the required equipment."""
    complete = True
    trip["equipment"] = {}
    for actor in members:
        key = str(actor.id)
        inventory = world.inventories[key]
        required = {"fiber": 1}
        if trip.get("kind") == "boat" and not actor.metadata.get("boat_id"):
            required["boat"] = 1
        missing = {item: count - inventory.items.get(item, 0) for item, count in required.items()
                   if inventory.items.get(item, 0) < count}
        trip["equipment"][key] = missing
        active = decisions._lifecycle.active(actor.id)
        if active:
            if active[1].target.get("expedition_id") != trip["id"]:
                raise ValueError("A companion has other work")
            decisions._continue(world, actor, *active, tick)
            complete = False
            continue
        if not missing:
            continue
        complete = False
        item, amount = next(iter(missing.items()))
        action_type = ActionType.MOVE
        target = decisions._storage_trip(world, actor, item, amount, True)
        if target is None and item == "boat":
            recipe = decisions._resources.CRAFTING_RECIPES["boat"]
            if inventory.has(recipe):
                action_type, target = ActionType.CRAFT, {"item_type": "boat"}
            else:
                item, amount = next((m, n-inventory.items.get(m, 0)) for m, n in recipe.items()
                                    if inventory.items.get(m, 0) < n)
                target = decisions._storage_trip(world, actor, item, amount, True)
        if target is None:
            kinds = {"wood": (ResourceType.LOG, ResourceType.TREE), "fiber": (ResourceType.REEDS,)}
            for kind in kinds.get(item, ()):
                try:
                    target = decisions._resource_target(world, actor, kind)
                    action_type = ActionType.CHOP if kind == ResourceType.TREE else ActionType.GATHER
                    break
                except ValueError:
                    continue
        if target is None:
            raise ValueError(f"No known source of expedition equipment: {item}")
        if "resource_id" in target:
            decisions._resources.reserve(UUID(str(target["resource_id"])), key, tick, 20)
        target = {**target, "expedition_id": trip["id"]}
        goal, action = decisions._lifecycle.start(actor, GoalType.CRAFT, action_type, .6,
            f"Collect {item} for the shared expedition", tick, target)
        decisions._begin(world, actor, goal, action, tick)
    return complete
