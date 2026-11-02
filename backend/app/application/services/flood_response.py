"""Local flood safety and useful, knowledge-limited crossing projects."""
from collections import deque

from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.navigation import MovementPlan, MovementStatus
from app.domain.models.structure import StructureType
from app.application.services.hydrology import neighbors


def evacuate(service, world, citizen, tick):
    if any(citizen.metadata.get(k) for k in ("in_cave", "aboard", "dive_trip", "carried_by", "rescue_controlled")):
        return False
    tile = world.retrieve_tile(citizen.x, citizen.y)
    if not tile or not tile.metadata.get("flooded"):
        if citizen.metadata.pop("flood_evacuating", None):
            citizen.metadata["state"] = "idle"
        return False
    service._perception.observe(citizen.id, tick)
    key = str(citizen.id)
    warning = citizen.metadata.get("flood_warning", {})
    if warning.get("expires", -1) < tick:
        warning = {"x": citizen.x, "y": citizen.y, "expires": tick + 48, "tick": tick,
                   "source": key, "experience": "experienced"}
        citizen.metadata["flood_warning"] = warning
        episodes = world.episodes.setdefault(key, [])
        episodes.append(Episode(entity_id=citizen.id, episode_type=EpisodeType.DANGER,
                                tick=tick, x=citizen.x, y=citizen.y, importance=.9,
                                summary="Rising river water flooded my location; seek dry ground.",
                                details={"hazard": "flood", "consequence": "Evacuate and warn nearby citizens"}))
        del episodes[:-200]
    active = service._lifecycle.active(citizen.id)
    if active:
        service._lifecycle.fail(*active, tick, "Flood evacuation takes priority.")
    citizen.metadata.update(flood_evacuating=True, state="evacuate", indoors=False,
                            sheltered_sleep=False, last_decision_reason="Flooding: move to nearby known dry ground.")
    knowledge = world.entity_knowledge[key]
    start = (citizen.x, citizen.y)
    queue, parent = deque([start]), {start: None}
    destination = None
    while queue and len(parent) <= 128:
        pos = queue.popleft()
        here = world.retrieve_tile(*pos)
        if pos != start and here.walkable and not here.metadata.get("flooded"):
            destination = pos
            break
        for nxt in neighbors(*pos):
            other = world.retrieve_tile(*nxt)
            if nxt in parent or f"{nxt[0]},{nxt[1]}" not in knowledge.tiles or not other:
                continue
            if (not other.walkable and not other.metadata.get("flooded")) or service._navigation._structure_blocks(world, *nxt):
                continue
            parent[nxt] = pos
            queue.append(nxt)
    if destination is None:
        world.movement_plans.pop(key, None)
        citizen.metadata["last_decision_reason"] = "Flooded and no known dry escape route; awaiting safer conditions."
        return True
    path, pos = [], destination
    while pos is not None:
        path.append(pos)
        pos = parent[pos]
    world.movement_plans[key] = MovementPlan(entity_id=citizen.id,
        destination_x=destination[0], destination_y=destination[1], path=list(reversed(path)),
        status=MovementStatus.MOVING, planned_at_tick=tick)
    return True


def propose_bridge(service, world, citizen, tick):
    """One proposal per citizen/day; no free material, undiscovered targets or duplicate sites."""
    if tick < citizen.metadata.get("next_bridge_review", 0):
        return
    citizen.metadata["next_bridge_review"] = tick + 24
    if not citizen.needs or citizen.needs.energy < 45 or max(citizen.needs.hunger, citizen.needs.thirst) > 60:
        return
    if sum(s.structure_type == StructureType.BRIDGE and not s.completed for s in world.structures.values()) >= 2:
        return
    knowledge = world.entity_knowledge.get(str(citizen.id))
    if not knowledge:
        return
    for x, y in neighbors(citizen.x, citizen.y):
        if f"{x},{y}" not in knowledge.tiles:
            continue
        tile = world.retrieve_tile(x, y)
        opposite = (2 * x - citizen.x, 2 * y - citizen.y)
        far = world.retrieve_tile(*opposite)
        if not tile or tile.terrain.value != "WATER" or tile.walkable or not far or not far.walkable:
            continue
        if f"{opposite[0]},{opposite[1]}" not in knowledge.tiles or service._navigation._structure_blocks(world, *opposite):
            continue
        if any((s.x, s.y) == (x, y) for s in world.structures.values()):
            continue
        route = service._navigation._find_path(world, citizen, *opposite)
        if route is not None and len(route) <= 12:
            continue
        from app.application.services.construction_service import ConstructionService
        try:
            site = ConstructionService(service._repository).start_site(str(citizen.id), StructureType.BRIDGE, x, y)
        except ValueError:
            continue
        citizen.metadata["last_decision_reason"] = "Proposed a bridge to connect known banks without a long detour."
        citizen.metadata["bridge_project"] = str(site.id)
        service._perception.observe(citizen.id, tick)
        return


def warn_neighbors(communication, world, tick):
    citizens = [c for c in world.entities.values() if communication._available(c)]
    for sender in citizens:
        warning = sender.metadata.get("flood_warning", {})
        if warning.get("expires", -1) < tick or warning.get("experience") != "experienced":
            continue
        for recipient in citizens:
            if recipient.id == sender.id or sender.distance_squared_to(recipient.x, recipient.y) > 36:
                continue
            heard = recipient.metadata.get("flood_warning", {})
            if heard.get("tick", -1) >= warning["tick"]:
                continue
            communication.send(sender.id, recipient.id,
                f"The river flooded near ({warning['x']}, {warning['y']}). Avoid the low banks and head for dry ground!", tick)
            recipient.metadata["flood_warning"] = {**warning, "experience": "heard", "source": str(sender.id)}
            communication._memory.remember(recipient.id, EpisodeType.DANGER, tick,
                f"{sender.name} warned me about river flooding near ({warning['x']}, {warning['y']}).",
                .8, {"hazard": "flood", "experience": "heard", "source": str(sender.id),
                     "x": warning["x"], "y": warning["y"], "expires": warning["expires"]}, [sender.id])
