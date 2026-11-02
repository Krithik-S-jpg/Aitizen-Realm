"""Connected cave extraction and reserve-checked underwater towing."""
from collections import deque

from app.domain.models.navigation import MovementPlan, MovementStatus


def path_between(start, goal, allowed):
    start, goal = tuple(start), tuple(goal)
    queue, parents = deque([start]), {start: None}
    while queue:
        point = queue.popleft()
        if point == goal:
            path = [point]
            while parents[path[-1]] is not None:
                path.append(parents[path[-1]])
            return list(reversed(path))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = point[0]+dx, point[1]+dy
            if nxt in allowed and nxt not in parents:
                parents[nxt] = point
                queue.append(nxt)
    return None


def water_tiles(world, actor):
    return {(r.x, r.y) for r in world.entity_knowledge[str(actor.id)].tiles.values()
            if (t := world.retrieve_tile(r.x, r.y)) and t.terrain.value in {"WATER", "OCEAN"}}


def start(world, patient, helper):
    if patient.metadata.get("in_cave") and helper.metadata.get("in_cave"):
        if patient.metadata.get("cave_id") != helper.metadata.get("cave_id"):
            return None
        cave = world.caves[helper.metadata["cave_id"]]
        hx, hy = helper.metadata["cave_position"]
        px, py = patient.metadata["cave_position"]
        if (hx-px)**2+(hy-py)**2 > helper.perception_radius**2:
            return None
        allowed = {tuple(p) for p in cave["floor"]}
        approach = path_between(helper.metadata["cave_position"], patient.metadata["cave_position"], allowed)
        back = path_between(patient.metadata["cave_position"], (0, 0), allowed)
        mode = "cave"
    elif patient.metadata.get("dive_trip") and helper.metadata.get("dive_trip"):
        allowed = water_tiles(world, helper)
        approach = path_between((helper.x, helper.y), (patient.x, patient.y), allowed)
        shores = [(r.x, r.y) for r in world.entity_knowledge[str(helper.id)].tiles.values()
                  if (t := world.retrieve_tile(r.x, r.y)) and t.walkable]
        returns = [p for shore in shores if (p := path_between((patient.x, patient.y), shore, allowed | {shore}))]
        back = min(returns, key=len) if returns else None
        mode = "water"
    else:
        return None
    if not approach or not back:
        return None
    steps = len(approach)+len(back)-2
    if mode == "water" and (helper.metadata.get("oxygen", 100) < steps*12+24 or helper.needs.energy < steps*6+25):
        return None
    if mode == "cave" and helper.needs.energy < steps*2+25:
        return None
    return {"mode": mode, "environment": mode, "approach": approach, "return_route": back,
            "step": 1, "picked_up": False, "patient": str(patient.id), "helper": str(helper.id)}


def advance(world, rescue, patient, helper, tick):
    mode = rescue["mode"]
    route = rescue["return_route"] if rescue["picked_up"] else rescue["approach"]
    if rescue["step"] < len(route):
        point = route[rescue["step"]]
        if abs(point[0]-(helper.metadata["cave_position"][0] if mode == "cave" else helper.x)) + abs(
                point[1]-(helper.metadata["cave_position"][1] if mode == "cave" else helper.y)) != 1:
            raise ValueError("Rescue route changed; stop instead of teleporting")
        if mode == "cave":
            if tuple(point) not in {tuple(p) for p in world.caves[helper.metadata["cave_id"]]["floor"]}:
                raise ValueError("Cave passage blocked")
            helper.metadata["cave_position"] = list(point)
        else:
            helper.x, helper.y = point
        helper.needs.energy = max(0, helper.needs.energy-(6 if mode == "water" else 2))
        rescue["step"] += 1
    if rescue["picked_up"]:
        if mode == "cave":
            patient.metadata["cave_position"] = list(helper.metadata["cave_position"])
        else:
            patient.x, patient.y = helper.x, helper.y
    elif rescue["step"] >= len(route):
        rescue.update(picked_up=True, step=1)
        patient.metadata["carried_by"] = str(helper.id)
        helper.metadata["carrying_casualty"] = str(patient.id)
    if mode == "water":
        for e in (helper, patient):
            e.metadata["oxygen"] = max(0, float(e.metadata.get("oxygen", 100))-12)
            if e.metadata["oxygen"] == 0 and e.active:
                e.needs.health = max(0, e.needs.health-5)
    arrived = rescue["picked_up"] and rescue["step"] >= len(rescue["return_route"])
    if arrived:
        for e in (helper, patient):
            e.metadata.pop("rescue_controlled", None)
            if mode == "cave":
                e.metadata.update(in_cave=False, cave_position=[0, 0])
            else:
                e.metadata.update(dive_trip=False, underwater=False, oxygen=100, travel_mode="walk", aboard=False)
                boat = world.entities.get(str(e.metadata.get("boat_id", "")))
                if boat and boat.metadata.get("occupant") == str(e.id):
                    boat.metadata["occupant"] = ""
                e.metadata.pop("auto_voyage", None)
        rescue["extracted_tick"] = tick
    return arrived


def release(world, actor, tick):
    """Restore a physical self-return route after an interrupted rescue."""
    if not actor.metadata.pop("rescue_controlled", None):
        return
    if actor.metadata.get("in_cave"):
        cave = world.caves[actor.metadata["cave_id"]]
        path = path_between(actor.metadata["cave_position"], (0, 0), {tuple(p) for p in cave["floor"]})
        if path:
            actor.metadata.update(cave_route=path, cave_step=1)
    elif actor.metadata.get("dive_trip"):
        allowed = water_tiles(world, actor)
        origin = tuple(actor.metadata["dive_origin"])
        path = path_between((actor.x, actor.y), origin, allowed | {origin})
        if path:
            world.movement_plans[str(actor.id)] = MovementPlan(entity_id=actor.id,
                destination_x=origin[0], destination_y=origin[1], path=path, planned_at_tick=tick,
                status=MovementStatus.MOVING if len(path)>1 else MovementStatus.ARRIVED)
            actor.metadata["dive_returning"] = True
            if len(path) == 1:
                actor.metadata.update(dive_trip=False, underwater=False, oxygen=100)
