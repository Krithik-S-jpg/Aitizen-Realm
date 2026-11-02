"""Finite shore fisheries and fuel-backed food preparation."""
from app.domain.models.cognition import ActionType


def target(decisions, world, entity):
    if entity.diet == "vegetarian":
        raise ValueError("Vegetarian citizens choose plant food.")
    inventory = world.inventories[str(entity.id)]
    known = world.entity_knowledge[str(entity.id)]
    if inventory.items.get("raw_fish", 0) >= 1:
        for site in world.structures.values():
            if str(site.id) in known.structures and site.completed and site.structure_type.value == "CAMPFIRE" and site.fuel >= .5:
                result = decisions._site_target(world, entity, site.id, "cook")
                result.pop("supply_site", None)
                result["cook_fire"] = str(site.id)
                return ActionType.COOK, result
        raise ValueError("Cooking fish requires a known fueled campfire.")
    if inventory.items.get("fishing_rod", 0) < 1:
        if inventory.has({"wood": 2, "fiber": 2}):
            return ActionType.CRAFT, {"item_type": "fishing_rod"}
        raise ValueError("Fishing requires a rod (2 wood, 2 fiber).")
    if inventory.carried >= inventory.capacity:
        raise ValueError("No room for a catch.")
    for record in sorted(known.tiles.values(), key=lambda r: entity.distance_squared_to(r.x, r.y)):
        tile = world.retrieve_tile(record.x, record.y)
        if not tile or tile.terrain.value not in {"WATER", "OCEAN"} or tile.metadata.get("fish_stock", 5) < 1:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = tile.x + dx, tile.y + dy
            shore = world.retrieve_tile(x, y)
            if shore and shore.walkable and f"{x},{y}" in known.tiles and decisions._navigation._find_path(world, entity, x, y) is not None:
                return ActionType.FISH, {"x": x, "y": y, "water_x": tile.x, "water_y": tile.y}
    raise ValueError("No reachable known fishing shore remains.")


def advance(world, entity, action, tick):
    if entity.diet == "vegetarian":
        raise ValueError("This action conflicts with the citizen's diet.")
    inventory = world.inventories[str(entity.id)]
    fishing = action.action_type == ActionType.FISH
    if fishing:
        tile = world.retrieve_tile(int(action.target["water_x"]), int(action.target["water_y"]))
        if not tile or tile.terrain.value not in {"WATER", "OCEAN"} or entity.distance_squared_to(tile.x, tile.y) != 1:
            raise ValueError("Stand on shore beside the fishing target.")
        if inventory.items.get("fishing_rod", 0) < 1 or tile.metadata.get("fish_stock", 5) < 1 or inventory.capacity-inventory.carried < 1:
            raise ValueError("No rod, fish stock or carrying space remains.")
    else:
        fire = world.structures.get(str(action.target["cook_fire"]))
        ingredient = str(action.target.get("ingredient", "raw_fish"))
        if ingredient not in {"raw_fish", "meat"}:
            raise ValueError("Unknown cooking ingredient.")
        if not fire or not fire.completed or fire.structure_type.value != "CAMPFIRE" or fire.fuel < .5 or entity.distance_squared_to(fire.x, fire.y) > 2 or inventory.items.get(ingredient, 0) < 1:
            raise ValueError("Cooking needs raw fish beside a fueled campfire.")
    if action.target.get("last_work_tick") == tick:
        return None
    action.target["last_work_tick"] = tick
    entity.metadata["state"] = "fish" if fishing else "cook"
    action.work_required = 5 if fishing else 3
    action.progress += 1
    if action.progress < action.work_required:
        return None
    if fishing:
        tile.metadata["fish_stock"] = tile.metadata.get("fish_stock", 5) - 1
        inventory.add("raw_fish", 1)
        result = {"caught": "raw_fish", "quantity": 1}
    else:
        cooked = "cooked_meat" if ingredient == "meat" else "cooked_fish"
        inventory.consume({ingredient: 1})
        inventory.add(cooked, 1)
        fire.fuel -= .5
        result = {"cooked": cooked, "quantity": 1}
    entity.metadata["state"] = "idle"
    return result


def cooking_target(decisions, world, entity, ingredient):
    known = world.entity_knowledge[str(entity.id)]
    for site in world.structures.values():
        if str(site.id) in known.structures and site.completed and site.structure_type.value == "CAMPFIRE" and site.fuel >= .5:
            result = decisions._site_target(world, entity, site.id, "cook")
            result.pop("supply_site", None)
            result.update(cook_fire=str(site.id), ingredient=ingredient)
            return ActionType.COOK, result
    raise ValueError("Cooking requires a known fueled campfire.")
