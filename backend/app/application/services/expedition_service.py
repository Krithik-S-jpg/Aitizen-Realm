"""Optional exploration competes only after immediate survival and active work."""

from app.domain.models.calendar import calendar_at_tick, DayPhase
from app.domain.models.cognition import GoalType, ActionType
from app.domain.models.resource import ResourceType
from app.domain.models.navigation import MovementStatus
from app.application.services.cave_service import CaveService


def consider_expedition(decisions, world, entity, tick, threats):
    """Use known targets and existing physical actions, never create supplies."""
    needs = entity.needs
    if (
        not needs
        or needs.health < 70
        or needs.energy < 80
        or needs.hunger > 30
        or needs.thirst > 30
        or threats
        or calendar_at_tick(tick).phase != DayPhase.DAY
        or needs.body_temperature_c < 36
        or tick < entity.metadata.get("expedition_cooldown", 0)
    ):
        return False
    known = world.entity_knowledge.get(str(entity.id))
    if not known:
        return False
    plan = world.movement_plans.get(str(entity.id))
    if plan and plan.status == MovementStatus.MOVING:
        return bool(entity.metadata.get("expedition_approach"))
    entity.metadata.pop("expedition_approach", None)
    navigation = decisions._navigation
    try:
        for cave in world.caves.values():
            if (
                f"{cave['x']},{cave['y']}" in known.tiles
                and cave["id"] not in entity.metadata.get("explored_caves", [])
                and entity.distance_squared_to(cave["x"], cave["y"]) <= 16
            ):
                if entity.distance_squared_to(cave["x"], cave["y"]) <= 1:
                    CaveService(decisions._repository).enter(entity.id, tick)
                else:
                    navigation.plan(entity.id, cave["x"], cave["y"], tick)
                    entity.metadata["expedition_approach"] = True
                entity.metadata["last_decision_reason"] = (
                    "Needs are met; investigate a known unexplored cave entrance."
                )
                return True
        shores = []
        for record in known.tiles.values():
            tile = world.retrieve_tile(record.x, record.y)
            if (
                tile
                and tile.walkable
                and any(
                    (adj := world.retrieve_tile(*p))
                    and adj.terrain.value == "WATER"
                    and f"{p[0]},{p[1]}" in known.tiles
                    for p in navigation._neighbors((tile.x, tile.y))
                )
            ):
                shores.append(tile)
        if not shores:
            return False
        shore = min(shores, key=lambda t: entity.distance_squared_to(t.x, t.y))
        inventory = decisions._resources.inventory_for(str(entity.id))
        boat = world.entities.get(str(entity.metadata.get("boat_id", "")))
        if (
            entity.metadata.get("underwater_explored")
            and not boat
            and not inventory.has({"boat": 1})
        ):
            recipe = {"wood": 20.0, "fiber": 8.0}
            if inventory.has(recipe):
                action_type, target = ActionType.CRAFT, {"item_type": "boat"}
            else:
                if inventory.capacity - inventory.carried < 2:
                    return False
                material = "wood" if inventory.items.get("wood", 0) < 20 else "fiber"
                resource_type = (
                    ResourceType.LOG if material == "wood" else ResourceType.REEDS
                )
                try:
                    target = decisions._resource_target(world, entity, resource_type)
                except ValueError:
                    if material != "wood":
                        return False
                    target = decisions._resource_target(
                        world, entity, ResourceType.TREE
                    )
                resource = world.resources[str(target["resource_id"])]
                action_type = (
                    ActionType.CHOP
                    if resource.resource_type == ResourceType.TREE
                    else ActionType.GATHER
                )
                decisions._resources.reserve(resource.id, str(entity.id), tick, 20)
            reason = "Prepare a boat to explore known water safely; gather its real construction materials."
            goal, action = decisions._lifecycle.start(
                entity, GoalType.CRAFT, action_type, 0.35, reason, tick, target
            )
            entity.metadata["last_decision_reason"] = reason
            decisions._begin(world, entity, goal, action, tick)
            return True
        if boat:
            if entity.distance_squared_to(boat.x, boat.y) <= 1:
                navigation.boat_command(entity.id, "board", tick)
                entity.metadata.update(
                    auto_voyage="outbound", voyage_home=[boat.x, boat.y]
                )
                return True
            shore_candidates = [
                t for t in shores if (t.x - boat.x) ** 2 + (t.y - boat.y) ** 2 == 1
            ]
            if not shore_candidates:
                return False
            shore = min(
                shore_candidates, key=lambda t: entity.distance_squared_to(t.x, t.y)
            )
        if (entity.x, entity.y) != (shore.x, shore.y):
            navigation.plan(entity.id, shore.x, shore.y, tick)
            entity.metadata["expedition_approach"] = True
        elif inventory.has({"boat": 1}):
            navigation.boat_command(entity.id, "launch", tick)
        else:
            navigation.explore_underwater(entity.id, tick)
            entity.metadata["expedition_cooldown"] = tick + 24
        entity.metadata["last_decision_reason"] = (
            "Healthy, rested and fed: explore nearby known water before returning to daily needs."
        )
        return True
    except (ValueError, LookupError) as error:
        entity.metadata["expedition_blocked"] = str(error)
        entity.metadata["expedition_cooldown"] = tick + 12
        return False


def advance_auto_voyage(decisions, world, entity, tick):
    """One operation per tick; an autonomous voyage always returns to its launch."""
    stage = entity.metadata.get("auto_voyage")
    if not stage or entity.metadata.get("dive_trip"):
        return
    nav = decisions._navigation
    plan = world.movement_plans.get(str(entity.id))
    if plan and plan.status == MovementStatus.MOVING:
        return
    home = entity.metadata["voyage_home"]
    try:
        if stage == "outbound":
            known = world.entity_knowledge[str(entity.id)]
            targets = [
                r
                for r in known.tiles.values()
                if 1 <= entity.distance_squared_to(r.x, r.y) <= 4
                and (t := world.retrieve_tile(r.x, r.y))
                and t.terrain.value in {"WATER", "OCEAN"}
            ]
            targets.sort(
                key=lambda r: (
                    f"{r.x},{r.y}" in entity.metadata.get("marine_discoveries", {}),
                    -entity.distance_squared_to(r.x, r.y),
                )
            )
            for target in targets:
                try:
                    nav.boat_command(entity.id, "row", tick, target.x, target.y)
                    entity.metadata["auto_voyage"] = "dive"
                    return
                except ValueError:
                    continue
            entity.metadata["auto_voyage"] = "home"
        elif stage == "dive":
            entity.metadata["auto_voyage"] = "home"
            if (
                entity.needs.energy >= 80
                and entity.needs.hunger < 40
                and entity.needs.thirst < 40
            ):
                nav.explore_underwater(entity.id, tick)
        elif stage == "home":
            nav.boat_command(entity.id, "anchor", tick)
            nav.boat_command(entity.id, "store", tick)
            nav.boat_command(entity.id, "row", tick, *home)
            entity.metadata["auto_voyage"] = "land"
        elif stage == "land":
            nav.boat_command(entity.id, "anchor", tick)
            nav.boat_command(entity.id, "disembark", tick)
            entity.metadata.pop("auto_voyage", None)
            entity.metadata["expedition_cooldown"] = tick + 48
    except (ValueError, LookupError) as error:
        entity.metadata["expedition_blocked"] = str(error)
        entity.metadata["auto_voyage"] = "home"
