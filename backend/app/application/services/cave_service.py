"""Persistent connected cave interiors and bounded exploration trips."""

from collections import deque
from uuid import NAMESPACE_URL, uuid5

from app.domain.models.entity import Entity, EntityKind
from app.domain.models.calendar import calendar_at_tick, DayPhase
from app.domain.models.memory import EpisodeType
from app.application.services.memory_service import MemoryService
from app.application.services.marine_service import MarineService


class CaveService:
    """Own interior positions independently of the surface coordinate grid."""

    def __init__(self, repository):
        self.repository = repository

    def initialize(self, world):
        if world.caves_initialized:
            # Add chambers without invalidating saved paths or animal positions.
            for cave in world.caves.values():
                self._expand_chambers(cave, world.seed or 0)
                tile = world.retrieve_tile(cave["x"], cave["y"])
                if tile:
                    tile.metadata["cave"] = cave
            return
        occupied = set()
        for chunk in world.chunks.values():
            for tile in chunk.tiles.values():
                region = (tile.x // 24, tile.y // 24)
                if not tile.walkable or region in occupied or len(world.caves) >= 16:
                    continue
                if not any(
                    t and t.terrain.value == "MOUNTAIN"
                    for t in (
                        world.retrieve_tile(tile.x + dx, tile.y + dy)
                        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    )
                ):
                    continue
                if world.resources_at(tile.x, tile.y) or any(
                    s.x == tile.x and s.y == tile.y for s in world.structures.values()
                ):
                    continue
                occupied.add(region)
                key = str(uuid5(NAMESPACE_URL, f"cave:{world.seed}:{tile.x}:{tile.y}"))
                floor = {(0, 0)}
                point = (0, 0)
                for index in range(55):
                    dx, dy = [(1, 0), (-1, 0), (0, 1), (0, -1)][
                        int(
                            MarineService.sample(
                                tile.x, index, tile.y + (world.seed or 0)
                            )
                            * 4
                        )
                        % 4
                    ]
                    point = (
                        max(-4, min(4, point[0] + dx)),
                        max(-4, min(4, point[1] + dy)),
                    )
                    floor.add(point)
                cave = dict(
                    id=key, x=tile.x, y=tile.y, floor=[list(p) for p in sorted(floor)]
                )
                self._expand_chambers(cave, world.seed or 0)
                world.caves[key] = cave
                tile.metadata["cave"] = cave
                for index, species in enumerate(["bat", "cave_beetle", "bat"]):
                    at = sorted(floor)[(index * 5 + 3) % len(floor)]
                    animal = Entity(
                        id=uuid5(NAMESPACE_URL, f"{key}:{index}"),
                        kind=EntityKind.ANIMAL,
                        name=species.replace("_", " ").title(),
                        x=tile.x,
                        y=tile.y,
                        metadata=dict(
                            cave_id=key,
                            cave_animal=True,
                            cave_position=list(at),
                            species=species,
                            state="rest",
                        ),
                    )
                    world.entities[str(animal.id)] = animal
        world.caves_initialized = True

    @staticmethod
    def _expand_chambers(cave, seed):
        if cave.get("layout_version", 1) >= 2:
            CaveService._features(cave, seed)
            return
        floor = {tuple(p) for p in cave["floor"]}
        # Three irregular rooms linked by two-tile-wide corridors.
        side = -1 if MarineService.sample(cave["x"], cave["y"], seed) < 0.5 else 1
        rooms = [(0, 0, 3, 3), (side * 5, -4, 4, 3), (-side * 4, -6, 3, 3)]
        for cx, cy, rx, ry in rooms:
            for x in range(cx - rx, cx + rx + 1):
                for y in range(cy - ry, cy + ry + 1):
                    roughness = 0.85 + MarineService.sample(x, y, seed) * 0.25
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= roughness:
                        floor.add((x, y))
            x, y = 0, 0
            while (x, y) != (cx, cy):
                if x != cx:
                    x += 1 if cx > x else -1
                elif y != cy:
                    y += 1 if cy > y else -1
                floor.update({(x, y), (x, y + 1)})
        cave.update(floor=[list(p) for p in sorted(floor)], layout_version=2)
        CaveService._features(cave, seed)

    @staticmethod
    def _features(cave, seed):
        if cave.get("features_version") == 1:
            return
        features = cave.setdefault("features", {})
        for x, y in cave["floor"]:
            if abs(x) + abs(y) < 3:
                continue
            roll = MarineService.sample(x + cave["x"], y + cave["y"], seed + 819)
            kind = "ore" if roll < .07 else "pool" if roll < .11 else "inscription" if roll < .135 else "unstable" if roll < .16 else ""
            if kind:
                features.setdefault(f"{x},{y}", {"kind": kind, "remaining": 6 if kind == "ore" else 0})
        cave.setdefault("surveyed", [[0, 0]])
        cave["features_version"] = 1

    def _survey(self, world, entity, cave, tick):
        position = entity.metadata["cave_position"]
        floor = {tuple(p) for p in cave["floor"]}
        seen = {tuple(p) for p in cave.setdefault("surveyed", [[0, 0]])}
        seen.update(p for p in floor if abs(p[0]-position[0])+abs(p[1]-position[1]) <= 1)
        cave["surveyed"] = [list(p) for p in sorted(seen)]
        maps = entity.metadata.setdefault("cave_maps", {})
        personal = maps.setdefault(cave["id"], [])
        if position not in personal:
            personal.append(list(position))
        key = f"{position[0]},{position[1]}"
        feature = cave.get("features", {}).get(key)
        if feature and feature["kind"] == "inscription":
            site = next((site_id for site_id, site in world.ancient_sites.items()
                         if abs(site.get("x", -999)-cave["x"])+abs(site.get("y", -999)-cave["y"]) <= 12), None)
            if site:
                feature["surface_site_id"] = site
        if not feature:
            return
        discoveries = entity.metadata.setdefault("cave_discoveries", {})
        event_key = cave["id"] + ":" + key
        if event_key not in discoveries:
            discoveries[event_key] = {"kind": feature["kind"], "tick": tick, "position": list(position), "cave_id": cave["id"], "surface_site_id": feature.get("surface_site_id")}
            MemoryService(self.repository).remember(entity.id, EpisodeType.DISCOVERY, tick,
                f"Found {feature['kind']} in a cave at passage ({key}); the entrance route is recorded.",
                .85, discoveries[event_key])
        inventory = world.inventories.get(str(entity.id))
        if feature["kind"] == "ore" and inventory and inventory.items.get("stone_pickaxe", 0) >= 1:
            accepted = inventory.add("ore", min(1, feature["remaining"]))
            feature["remaining"] -= accepted
        if feature["kind"] == "unstable":
            entity.metadata["cave_warning"] = {"cave_id": cave["id"], "position": list(position), "tick": tick,
                                               "message": "Loose rocks ahead. Return by the marked route."}
            entity.metadata["cave_return_requested"] = True

    def enter(self, entity_id, tick):
        world = self.repository.get()
        entity = world.entities.get(str(entity_id)) if world else None
        if not entity or not entity.active or entity.kind != EntityKind.AGENT:
            raise ValueError("Select an active citizen.")
        from app.application.services.family_service import adult
        if not adult(entity):
            raise ValueError("Only adults can explore caves.")
        if (
            entity.metadata.get("in_cave")
            or entity.metadata.get("dive_trip")
            or entity.metadata.get("aboard")
        ):
            raise ValueError("Finish the current expedition first.")
        if not entity.needs or entity.needs.energy < 65 or entity.needs.health < 60:
            raise ValueError("Cave exploration requires 65 energy and 60 health.")
        self.initialize(world)
        caves = [
            c
            for c in world.caves.values()
            if entity.distance_squared_to(c["x"], c["y"]) <= 1
        ]
        if not caves:
            raise ValueError("Walk to a cave entrance first.")
        cave = caves[0]
        floor = {tuple(p) for p in cave["floor"]}
        parents = {(0, 0): None}
        queue = deque([(0, 0)])
        while queue:
            point = queue.popleft()
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nxt = point[0] + dx, point[1] + dy
                if nxt in floor and nxt not in parents:
                    parents[nxt] = point
                    queue.append(nxt)
        seen = {tuple(p) for p in entity.metadata.get("cave_maps", {}).get(cave["id"], [])}
        unseen = [p for p in parents if p not in seen and p != (0, 0)]
        goal = unseen[0] if seen and unseen else next(reversed(parents))
        route = [goal]
        while parents[route[-1]] is not None:
            route.append(parents[route[-1]])
        route.reverse()
        inventory = world.inventories.get(str(entity.id))
        prepared = bool(inventory and inventory.has({"lamp": 1, "rope": 1})
                        and any(inventory.items.get(item, 0) >= 1 for item in ("food", "fruit", "bread", "cooked_meat", "cooked_fish")))
        route = route[:min(14, max(2, int((entity.needs.energy - 35) / 3)))] if prepared else route[:6]
        entity.metadata["cave_prepared"] = prepared
        entity.metadata.pop("cave_return_requested", None)
        route += list(reversed(route[:-1]))
        plan = world.movement_plans.get(str(entity.id))
        if plan:
            from app.domain.models.navigation import MovementStatus

            plan.status = MovementStatus.CANCELLED
        entity.x, entity.y = cave["x"], cave["y"]
        entity.metadata.update(
            in_cave=True,
            cave_id=cave["id"],
            cave_position=[0, 0],
            cave_route=route,
            cave_step=1,
            cave_returning=False,
            cave_tick=tick,
            state="cave_explore",
            last_decision_reason=("Survey with lamp, rope and provisions; keep the return route marked." if prepared else "Scout entrance passages; bring a lamp, rope and food to explore farther."),
        )
        return cave

    def advance_all(self, tick):
        world = self.repository.get()
        if not world:
            return
        self.initialize(world)
        for entity in world.entities.values():
            data = entity.metadata
            if data.get("rescue_controlled"):
                continue
            if (
                not entity.active
                or not data.get("cave_id")
                or data.get("cave_tick", -1) >= tick
            ):
                continue
            cave = world.caves.get(data["cave_id"])
            if not cave:
                continue
            data["cave_tick"] = tick
            if data.get("in_cave"):
                route = data["cave_route"]
                step = data["cave_step"]
                if step < len(route):
                    data["cave_position"] = list(route[step])
                    data["cave_step"] += 1
                    entity.needs.energy = max(0, entity.needs.energy - 1)
                    self._survey(world, entity, cave, tick)
                    if (data.pop("cave_return_requested", False) or entity.needs.energy < 35) and not data.get("cave_returning"):
                        visited = route[:data["cave_step"]]
                        data["cave_route"] = visited + list(reversed(visited[:-1]))
                        data["cave_returning"] = True
                        route = data["cave_route"]
                if data["cave_step"] >= len(route):
                    data.update(
                        in_cave=False, state="idle", expedition_cooldown=tick + 48
                    )
                    known = data.setdefault("explored_caves", [])
                    if cave["id"] not in known:
                        known.append(cave["id"])
                        MemoryService(self.repository).remember(
                            entity.id,
                            EpisodeType.DISCOVERY,
                            tick,
                            "Explored a cave and found a safe route back to its entrance.",
                            0.8,
                            {"cave_id": cave["id"]},
                        )
                continue
            if not data.get("cave_animal"):
                continue
            point = tuple(data["cave_position"])
            floor = {tuple(p) for p in cave["floor"]}
            visitors = [
                e
                for e in world.entities.values()
                if e.active
                and e.metadata.get("in_cave")
                and e.metadata.get("cave_id") == cave["id"]
            ]
            threats = [
                tuple(e.metadata["cave_position"])
                for e in visitors
                if sum((a - b) ** 2 for a, b in zip(point, e.metadata["cave_position"]))
                < 9
            ]
            rest = (
                data["species"] == "bat"
                and calendar_at_tick(tick).phase == DayPhase.DAY
                and not threats
            )
            data["state"] = "rest" if rest else "flee" if threats else "forage"
            if rest:
                continue
            options = [
                p for p in floor if abs(p[0] - point[0]) + abs(p[1] - point[1]) == 1
            ]
            if options:
                data["cave_position"] = list(
                    max(
                        options,
                        key=lambda p: (
                            min(
                                sum((a - b) ** 2 for a, b in zip(p, t)) for t in threats
                            )
                            if threats
                            else MarineService.sample(*p, tick)
                        ),
                    )
                )
