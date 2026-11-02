"""Finite resource brushes and time-limited local weather experiments."""
import hashlib
import json
from copy import deepcopy
from app.application.services import world_editor
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.navigation import MovementStatus

RESOURCES = {"TREE", "STONE", "BUSH", "HERB", "ORE"}
SCENARIOS = {"FOOD_GROVE": ("resource", "BUSH"), "STONE_OUTCROP": ("resource", "STONE"),
             "RAIN_TEST": ("weather", "RAIN"), "DRY_SPELL": ("weather", "CLEAR")}


def resolve(tool, choice):
    if tool == "scenario":
        if choice not in SCENARIOS:
            raise ValueError("Unknown scenario preset.")
        return SCENARIOS[choice]
    return tool, choice


def preview(world, x, y, radius, tool, choice, tick):
    tool, choice = resolve(tool, choice)
    if tool not in {"resource", "weather"} or radius not in range(3):
        raise ValueError("Unsupported editor tool or radius.")
    result = world_editor.preview(world, x, y, radius, "GRASS", tick)
    result.pop("terrain", None)
    if tool == "resource":
        if choice not in RESOURCES:
            raise ValueError("Unsupported resource.")
        for point in result["tiles"]:
            tile = world.retrieve_tile(point["x"], point["y"])
            if tile and (not tile.walkable or tile.terrain.value in {"WATER", "OCEAN", "ICE", "VOLCANIC"}):
                result["blocked"].append("Resources require dry, walkable terrain.")
        result["description"] = f"Place {len(result['tiles'])} finite {choice.lower()} nodes. Existing objects are never replaced."
    else:
        if choice not in {"RAIN", "SNOW", "CLEAR"}:
            raise ValueError("Unsupported weather.")
        # Weather can cover occupied land: no terrain or objects are replaced.
        result["blocked"] = [b for b in result["blocked"] if "outside loaded" in b]
        if sum(p["expires"] > tick for p in world.weather_patches) >= 4:
            result["blocked"].append("At most four active weather patches; wait or undo.")
        result["description"] = f"Local {choice.lower()} at ({x},{y}), radius {radius}, for 48 simulation ticks. Newer overlapping patches win."
    result["token"] = hashlib.sha256(json.dumps([result["token"], tool, choice, world.weather_patches], sort_keys=True).encode()).hexdigest()
    result["can_apply"] = not result["blocked"]
    return result


def apply(world, x, y, radius, tool, choice, tick, token):
    check = preview(world, x, y, radius, tool, choice, tick)
    if check["token"] != token or not check["can_apply"]:
        raise ValueError("Preview is stale or blocked. Preview again; nothing changed.")
    tool, choice = resolve(tool, choice)
    edit = {"tick": tick, "tool": tool}
    if tool == "resource":
        nodes = [ResourceNode(resource_type=ResourceType(choice), x=p["x"], y=p["y"],
                    quantity=30, capacity=30, produce_type="fruit" if choice == "BUSH" else None,
                    produce_quantity=12 if choice == "BUSH" else 0, produce_capacity=12 if choice == "BUSH" else 0)
                 for p in check["tiles"]]
        edit["resources"] = [n.model_dump(mode="json") for n in nodes]
        for node in nodes:
            world.add_resource(node)
        coordinates = {(node.x, node.y) for node in nodes}
        for plan in world.movement_plans.values():
            if any(tuple(point) in coordinates for point in plan.path):
                plan.status = MovementStatus.CANCELLED
    else:
        edit["before_weather"] = deepcopy(world.weather_patches)
        world.weather_patches = [p for p in world.weather_patches if p["expires"] > tick]
        world.weather_patches.append({"x": x, "y": y, "radius": radius, "weather": choice, "intensity": 0.0 if choice == "CLEAR" else .85, "expires": tick + 48})
        edit["after_weather"] = deepcopy(world.weather_patches)
    world.editor_history.append(edit)
    del world.editor_history[:-20]
    world.editor_revision += 1
    return {"changed": len(check["tiles"]), "undo_available": True, "description": check["description"]}


def undo(world, edit):
    if edit["tool"] == "resource":
        for snapshot in edit["resources"]:
            node = world.resources.get(snapshot["id"])
            if node is None or node.model_dump(mode="json") != snapshot:
                raise ValueError("Placed resources changed; unsafe undo refused.")
        for snapshot in edit["resources"]:
            world.resources.pop(snapshot["id"])
    else:
        if world.weather_patches != edit["after_weather"]:
            raise ValueError("Weather changed; unsafe undo refused.")
        world.weather_patches = deepcopy(edit["before_weather"])
    world.editor_history.pop()
    world.editor_revision += 1
    return {"changed": len(edit.get("resources", [1])), "undo_available": bool(world.editor_history)}


def local_weather(world, x, y, calendar, tick):
    from app.domain.models.calendar import WeatherType
    for patch in reversed(world.weather_patches):
        if patch["expires"] > tick and (x-patch["x"])**2 + (y-patch["y"])**2 <= patch["radius"]**2:
            return calendar.model_copy(update={"weather": WeatherType(patch["weather"]), "weather_intensity": patch["intensity"]})
    return calendar
