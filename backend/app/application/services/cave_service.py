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
        goal = next(reversed(parents))
        route = [goal]
        while parents[route[-1]] is not None:
            route.append(parents[route[-1]])
        route.reverse()
        route = route[:6]
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
            cave_tick=tick,
            state="cave_explore",
            last_decision_reason="Explore a connected cave passage, then return through its entrance.",
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
