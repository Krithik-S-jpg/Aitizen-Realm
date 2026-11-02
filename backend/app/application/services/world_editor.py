"""Atomic, preview-validated terrain brushes; bounded undo without simulation rewind."""
import hashlib
import json
from app.domain.models.world import TerrainType
from app.domain.models.navigation import MovementStatus
from app.application.services.world_generator import WorldGenerator

ALLOWED = {"GRASS", "DIRT", "SAND", "FOREST", "WATER", "STONE", "MOUNTAIN"}


def preview(world, x, y, radius, terrain, tick):
    if terrain not in ALLOWED or radius not in range(3):
        raise ValueError("Choose a supported terrain and brush radius 0–2.")
    positions = [(tx, ty) for tx in range(x-radius, x+radius+1) for ty in range(y-radius, y+radius+1) if (tx-x)**2 + (ty-y)**2 <= radius**2]
    occupied = {(e.x, e.y) for e in world.entities.values()}
    occupied |= {(s.x, s.y) for s in world.structures.values()}
    occupied |= {(r.x, r.y) for r in world.resources.values()}
    occupied |= {(h["x"], h["y"]) for h in world.ecology.get("homes", {}).values()}
    snapshots, blocked = [], []
    for tx, ty in positions:
        tile = world.retrieve_tile(tx, ty)
        if tile is None or not (0 <= tx < world.width and 0 <= ty < world.height):
            blocked.append(f"({tx},{ty}): outside loaded world")
            continue
        snapshots.append(tile.model_dump(mode="json"))
        if (tx, ty) in occupied or any(tile.metadata.get(k) for k in ("cave", "marine", "ancient_site", "flooded")):
            blocked.append(f"({tx},{ty}): occupied or protected habitat/site")
    payload = {"tiles": snapshots, "terrain": terrain, "tick": tick, "revision": world.editor_revision}
    token = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"token": token, "tiles": [{"x": tx, "y": ty} for tx, ty in positions], "blocked": blocked, "can_apply": not blocked, "terrain": terrain}


def apply(world, x, y, radius, terrain, tick, token):
    check = preview(world, x, y, radius, terrain, tick)
    if token != check["token"]:
        raise ValueError("World changed since preview. Preview this brush again.")
    if check["blocked"]:
        raise ValueError("Brush intersects occupied or protected tiles; nothing changed.")
    before, after = [], []
    for pos in check["tiles"]:
        tile = world.retrieve_tile(pos["x"], pos["y"])
        before.append(tile.model_dump(mode="json"))
        tile.terrain = TerrainType(terrain)
        tile.walkable = terrain != "WATER"
        tile.movement_cost = WorldGenerator._movement_cost(tile.terrain)
        tile.metadata = {"variant": tile.metadata.get("variant", 0), "edited": True,
                         "elevation": .8 if terrain == "MOUNTAIN" else .2 if terrain == "WATER" else .45}
        after.append(tile.model_dump(mode="json"))
    world.editor_history.append({"before": before, "after": after, "tick": tick})
    del world.editor_history[:-20]
    invalidate(world, {(p["x"], p["y"]) for p in check["tiles"]})
    return {"changed": len(before), "undo_available": True}


def invalidate(world, coordinates):
    world.editor_revision += 1
    world.hydrology["banks"] = [bank for bank in world.hydrology.get("banks", []) if (bank["x"], bank["y"]) not in coordinates]
    world.hydrology["chunk_count"] = -1
    for plan in world.movement_plans.values():
        if any(tuple(p) in coordinates for p in plan.path):
            plan.status = MovementStatus.CANCELLED


def undo(world, tick):
    if not world.editor_history:
        raise ValueError("No terrain edits to undo.")
    edit = world.editor_history[-1]
    if edit["tick"] != tick:
        raise ValueError("Simulation advanced since this edit; undo would overwrite newer state.")
    if "tool" in edit:
        from app.application.services.editor_tools import undo as undo_tool
        return undo_tool(world, edit)
    for snapshot in edit["after"]:
        tile = world.retrieve_tile(snapshot["x"], snapshot["y"])
        if tile is None or tile.model_dump(mode="json") != snapshot:
            raise ValueError("Edited terrain changed; unsafe undo refused.")
        if any((e.x, e.y) == (tile.x, tile.y) for e in world.entities.values()) or any((s.x, s.y) == (tile.x, tile.y) for s in world.structures.values()) or any((r.x, r.y) == (tile.x, tile.y) for r in world.resources.values()):
            raise ValueError("An object now occupies this edit; unsafe undo refused.")
    from app.domain.models.world import Tile
    for snapshot in edit["before"]:
        current = world.retrieve_tile(snapshot["x"], snapshot["y"])
        restored = Tile.model_validate(snapshot)
        current.terrain, current.walkable = restored.terrain, restored.walkable
        current.movement_cost, current.metadata = restored.movement_cost, restored.metadata
    world.editor_history.pop()
    invalidate(world, {(p["x"], p["y"]) for p in edit["before"]})
    return {"changed": len(edit["before"]), "undo_available": bool(world.editor_history)}
