"""Seeded archaeological facts, private evidence and knowledge-led investigation."""
import hashlib
import random

from app.domain.models.entity import EntityKind, KnowledgeRecord
from app.domain.models.memory import Episode, EpisodeType


def initialize(world):
    if world.secrets_initialized or world.seed is None:
        return
    world.secrets_initialized = True
    rng = random.Random(f"history-v1:{world.seed}:{world.width}:{world.height}")
    remaining = {(x, y) for x in range(world.width) for y in range(world.height)
                 if (t := world.retrieve_tile(x, y)) and t.walkable}
    largest = set()
    for root in sorted(remaining):
        if root not in remaining:
            continue
        remaining.remove(root)
        component, queue = {root}, [root]
        for x, y in queue:
            for p in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if p in remaining:
                    remaining.remove(p)
                    component.add(p)
                    queue.append(p)
        if len(component) > len(largest):
            largest = component
    if len(largest) < 12:
        return
    occupied = {(r.x, r.y) for r in world.resources.values()} | {(s.x, s.y) for s in world.structures.values()}
    pool = sorted(largest - occupied)
    if len(pool) < 3:
        return
    first = rng.choice(pool)
    chosen = [first]
    for _ in range(2):
        eligible = [p for p in pool if all((p[0]-q[0])**2+(p[1]-q[1])**2 >= 9 for q in chosen)]
        if not eligible:
            return
        chosen.append(rng.choice(eligible))
    culture = rng.choice(["Reedkeepers", "Amber Cartographers", "Moon Orchard settlers", "Stonewater navigators"])
    cause = rng.choice(["a prolonged drought", "a river changing course", "a succession of harsh winters"])
    age = rng.randrange(80, 401)
    kinds = ["inscription", "ruined_tower", "abandoned_settlement"]
    names = [f"{culture} waystone", "Broken watchtower", f"Lost home of the {culture}"]
    artifacts = ["Carved route tablet", "Bronze survey lens", "Ceramic household seal"]
    ids = [f"antiquity:{world.seed}:{i}" for i in range(3)]
    for i, (x, y) in enumerate(chosen):
        next_point = chosen[i+1] if i < 2 else None
        evidence = (f"A carved route points to ({next_point[0]}, {next_point[1]})."
                    if next_point else f"A sealed record says the {culture} left after {cause}, about {age} years ago.")
        site = dict(id=ids[i], x=x, y=y, kind=kinds[i], name=names[i], artifact=artifacts[i],
                    evidence=evidence, next_id=ids[i+1] if i < 2 else None,
                    next_position=list(next_point) if next_point else None,
                    mystery=f"The departure of the {culture}", discovered_by={}, inspected_by={})
        world.ancient_sites[ids[i]] = site
        world.retrieve_tile(x, y).metadata["ancient_site"] = {k: site[k] for k in ("id", "kind", "name")}


def interests(world, actor):
    if "curiosity" not in actor.metadata:
        digest = hashlib.sha256(f"{world.seed}:{actor.id}".encode()).digest()
        actor.metadata["curiosity"] = {name: round(.25+digest[i]/340, 2)
            for i, name in enumerate(("history", "wildlife", "geography", "unusual"))}
    return actor.metadata["curiosity"]


def observe(world, actor, tick):
    if actor.kind != EntityKind.AGENT:
        return
    initialize(world)
    interests(world, actor)
    if any(actor.metadata.get(k) for k in ("in_cave", "underwater", "dive_trip")):
        return
    knowledge = world.entity_knowledge[str(actor.id)]
    for key, site in world.ancient_sites.items():
        distance = actor.distance_squared_to(site["x"], site["y"])
        if distance > actor.perception_radius**2:
            continue
        site["discovered_by"].setdefault(str(actor.id), tick)
        inspected = distance <= 1
        old = knowledge.discoveries.get(key)
        if old and old.data.get("inspected") and distance > 1:
            continue
        # Do not downgrade a personally inspected fact to a distant sighting.
        inspected = inspected or bool(old and old.confidence == 1 and old.data.get("inspected"))
        data = {k: site[k] for k in ("id", "kind", "name", "mystery")}
        data["inspected"] = inspected
        if inspected:
            data.update({k: site[k] for k in ("artifact", "evidence", "next_id", "next_position")})
            site["inspected_by"].setdefault(str(actor.id), tick)
        if old is None or (inspected and not old.data.get("inspected")) or old.confidence < 1:
            knowledge.discoveries[key] = KnowledgeRecord(key=key, category="discovery", x=site["x"], y=site["y"],
                first_seen_tick=old.first_seen_tick if old else tick, last_seen_tick=tick, learned_at_tick=tick, data=data)
            world.episodes.setdefault(str(actor.id), []).append(Episode(entity_id=actor.id,
                episode_type=EpisodeType.DISCOVERY, tick=tick, x=actor.x, y=actor.y, importance=.85,
                summary=(f"Inspected {site['name']}: {site['evidence']}" if inspected else f"Spotted {site['name']}."),
                details={"site_id": key, "inspected": inspected}))


def target(world, actor):
    knowledge = world.entity_knowledge[str(actor.id)]
    goals = []
    for key, record in knowledge.discoveries.items():
        if not record.data.get("inspected") or record.confidence < 1:
            goals.append((record.x, record.y, key))
        elif record.data.get("next_position"):
            nxt = knowledge.discoveries.get(record.data.get("next_id"))
            if not nxt or not nxt.data.get("inspected"):
                goals.append((*record.data["next_position"], record.data["next_id"]))
    if not goals:
        return None
    x, y, key = min(goals, key=lambda p: actor.distance_squared_to(p[0], p[1]))
    candidates = [r for r in knowledge.tiles.values() if r.data.get("walkable")
                  and (r.x, r.y) != (actor.x, actor.y)]
    from app.application.services.navigation_service import NavigationService
    allowed = {(r.x, r.y) for r in candidates if not NavigationService._structure_blocks(world, r.x, r.y)}
    reachable, queue = {(actor.x, actor.y)}, [(actor.x, actor.y)]
    for ax, ay in queue:
        for point in ((ax+1, ay), (ax-1, ay), (ax, ay+1), (ax, ay-1)):
            if point in allowed and point not in reachable:
                reachable.add(point)
                queue.append(point)
    candidates = [r for r in candidates if (r.x, r.y) in reachable]
    warning = actor.metadata.get("wildlife_warning", {})
    candidates = [r for r in candidates if not (warning.get("expires", -1) >= knowledge.last_observation_tick
                  and (r.x-warning.get("x", -999))**2+(r.y-warning.get("y", -999))**2 <= 36)]
    if not candidates:
        return None
    destination = min(candidates, key=lambda r: ((r.x-x)**2+(r.y-y)**2, actor.distance_squared_to(r.x, r.y)))
    return {"x": destination.x, "y": destination.y, "purpose": "investigate", "site_id": key}


def frontier_interest(actor, knowledge, tile):
    """Private preferences influence equally useful frontiers without fixed jobs."""
    preferences = actor.metadata.get("curiosity", {})
    terrain = tile.data.get("terrain", "grass")
    geography = float(preferences.get("geography", 0)) * (terrain not in {"grass", "sand"})
    wildlife = float(preferences.get("wildlife", 0)) * any(
        r.data.get("kind", "").lower() == "animal" and (r.x-tile.x)**2+(r.y-tile.y)**2 <= 16
        for r in knowledge.entities.values())
    unusual = float(preferences.get("unusual", 0)) * (terrain in {"mountain", "wetland", "snow"})
    return geography + wildlife + unusual


def journal(world):
    entries = []
    for key, site in world.ancient_sites.items():
        if not site["discovered_by"]:
            continue
        entry = {k: site[k] for k in ("id", "x", "y", "kind", "name", "mystery")}
        entry["discoverers"] = [{"name": world.entities[k].name if k in world.entities else "Unknown citizen", "tick": tick}
                                for k, tick in site["discovered_by"].items()]
        entry["inspected"] = bool(site["inspected_by"])
        entry["interpretations"] = site.get("interpretations", [])
        if entry["inspected"]:
            entry.update({k: site[k] for k in ("artifact", "evidence", "next_id", "next_position")})
        entry["accounts"] = [{"citizen": e.name, "confidence": r.confidence,
                               "source": world.entities[str(r.source_entity_id)].name if str(r.source_entity_id) in world.entities else "direct observation"}
            for e in world.entities.values() if (k := world.entity_knowledge.get(str(e.id)))
            and (r := k.discoveries.get(key))]
        entry["expeditions"] = [t["id"] for t in world.expeditions.values()
                               if any(k in site["inspected_by"] and site["inspected_by"][k] >= t["started_tick"]
                                      and site["inspected_by"][k] <= t.get("finished_tick", float("inf")) for k in t["members"])]
        entries.append(entry)
    return entries
