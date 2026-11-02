"""Known, bounded party routes and existing cave/boat state machines."""
from app.application.services.cave_service import CaveService
from app.domain.models.navigation import MovementStatus


def itineraries(decisions, world, members, survey):
    options = [survey]
    common = set(world.entity_knowledge[str(members[0].id)].tiles) & set(world.entity_knowledge[str(members[1].id)].tiles)
    for cave in world.caves.values():
        point = cave["x"], cave["y"]
        if f"{point[0]},{point[1]}" not in common:
            continue
        if all(cave["id"] in e.metadata.get("explored_caves", []) for e in members):
            continue
        paths = [decisions._navigation._find_path(world, e, *point) for e in members]
        if all(p and len(p) <= 6 for p in paths):
            options.insert(0, {"kind": "cave", "cave_id": cave["id"], "destination": list(point),
                "targets": {str(e.id): list(point) for e in members}})
            break
    # Both citizens must know a nearby shore; no global water knowledge is supplied.
    for key in sorted(common):
        x, y = map(int, key.split(","))
        tile = world.retrieve_tile(x, y)
        if not tile or not tile.walkable:
            continue
        water = [t for t in world.get_neighbors(x, y) if t.terrain.value in {"WATER", "OCEAN"}
                 and f"{t.x},{t.y}" in common]
        paths = [decisions._navigation._find_path(world, e, x, y) for e in members] if water else []
        if paths and all(p and len(p) <= 6 for p in paths):
            # Existing vessels must already be at this shore, never remotely recalled.
            boats = [world.entities.get(str(e.metadata.get("boat_id", ""))) for e in members]
            if any(b and (not b.active or b.metadata.get("occupant") or abs(b.x-x)+abs(b.y-y) > 1) for b in boats):
                continue
            options.insert(0, {"kind": "boat", "destination": [x, y],
                "targets": {str(e.id): [x, y] for e in members}})
            break
    from app.application.services.expedition_camping import offer
    overnight = offer(decisions, world, members)
    if overnight:
        options.insert(0, overnight)
    return options


def explore(decisions, world, trip, members, tick):
    """Returns True while the party owns an interior/vessel activity."""
    if trip["phase"] == "outbound" and trip.get("kind") in {"cave", "boat"} and all(
            [e.x, e.y] == trip["targets"][str(e.id)] for e in members):
        if trip["kind"] == "cave":
            # Validate both before entry, avoiding a half-entered group.
            if any(e.needs.energy < 65 or e.needs.health < 60 for e in members):
                trip.update(phase="returning", reason="Cave entry reserves insufficient")
                return False
            for e in members:
                e.metadata.pop("party_cave_return", None)
                CaveService(decisions._repository).enter(e.id, tick)
            trip.update(phase="cave_exploring", reason="Explore together and retrace the entrance route")
        else:
            trip.update(phase="boat_exploring", reason="Launch a two-boat expedition and return to shore")
            trip["boat_started"] = []
    if trip["phase"] == "cave_exploring":
        if any(e.needs.critical or e.needs.energy < 55 for e in members):
            for e in members:
                data = e.metadata
                if data.get("in_cave") and not data.get("party_cave_return"):
                    visited = data["cave_route"][:data["cave_step"]]
                    data.update(cave_route=list(reversed(visited)), cave_step=1, party_cave_return=True)
        if any(e.metadata.get("in_cave") for e in members):
            return True
        trip.update(phase="returning", reason="Cave party back at entrance")
    if trip["phase"] == "boat_exploring":
        from app.application.services.expedition_service import advance_auto_voyage
        for e in members:
            key = str(e.id)
            if key not in trip["boat_started"]:
                if not e.metadata.get("boat_id"):
                    decisions._navigation.boat_command(e.id, "launch", tick)
                decisions._navigation.boat_command(e.id, "board", tick)
                e.metadata.update(auto_voyage="outbound", voyage_home=[e.x, e.y])
                trip["boat_started"].append(key)
            if any(p.needs.critical or p.needs.energy < 55 for p in members) or tick-trip.get("departed_tick", tick) > 24:
                if e.metadata.get("dive_trip"):
                    decisions._navigation.return_from_dive(e.id, tick)
                elif e.metadata.get("aboard") and e.metadata.get("auto_voyage") not in {"home", "land"}:
                    decisions._navigation.boat_command(e.id, "anchor", tick)
                    e.metadata["auto_voyage"] = "home"
            advance_auto_voyage(decisions, world, e, tick)
        if any(e.metadata.get("aboard") or e.metadata.get("dive_trip") for e in members):
            return True
        trip.update(phase="returning", reason="Boat party safely disembarked")
    return False
