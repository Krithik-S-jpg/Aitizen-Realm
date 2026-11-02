"""Bounded seasonal river simulation. Floods never replace underlying terrain."""
import heapq

from app.domain.models.calendar import Season, WeatherType
from app.domain.models.world import TerrainType


def neighbors(x, y):
    return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))


def carve_river(world):
    """Carve one connected drainage channel to existing water in a new world."""
    tiles = [t for c in world.chunks.values() for t in c.tiles.values()]
    if not tiles or not any(t.terrain in {TerrainType.WATER, TerrainType.OCEAN} for t in tiles):
        return
    source = max(tiles, key=lambda t: (t.metadata.get("elevation", 0), -t.x, -t.y))
    start = (source.x, source.y)
    frontier, cost, parent = [(0, start)], {start: 0}, {start: None}
    outlet = None
    while frontier:
        score, pos = heapq.heappop(frontier)
        if score != cost[pos]:
            continue
        tile = world.retrieve_tile(*pos)
        if tile.terrain in {TerrainType.WATER, TerrainType.OCEAN}:
            outlet = pos
            break
        for nxt in neighbors(*pos):
            other = world.retrieve_tile(*nxt)
            if other is None:
                continue
            uphill = max(0, other.metadata.get("elevation", 0) - tile.metadata.get("elevation", 0))
            candidate = score + 1 + uphill * 100
            if candidate < cost.get(nxt, float("inf")):
                cost[nxt], parent[nxt] = candidate, pos
                heapq.heappush(frontier, (candidate, nxt))
    channel = set()
    while outlet is not None:
        channel.add(outlet)
        tile = world.retrieve_tile(*outlet)
        if tile.terrain != TerrainType.OCEAN:
            tile.terrain, tile.walkable = TerrainType.WATER, False
            tile.metadata["river"] = True
        outlet = parent[outlet]
    world.resources = {k: r for k, r in world.resources.items() if (r.x, r.y) not in channel}


def advance(world, tick, calendar):
    """Update only cached low banks once per tick; old worlds retain their terrain."""
    state = world.hydrology
    if state.get("tick") == tick:
        return
    if "banks" not in state or state.get("chunk_count") != len(world.chunks):
        banks = {}
        for bank in state.get("banks", []):
            tile = world.retrieve_tile(bank["x"], bank["y"])
            if tile is not None:
                tile.walkable = bank["walkable"]
        for chunk in world.chunks.values():
            for water in chunk.tiles.values():
                if water.terrain != TerrainType.WATER:
                    continue
                for x, y in neighbors(water.x, water.y):
                    tile = world.retrieve_tile(x, y)
                    if tile is None or not tile.walkable or tile.terrain not in {
                        TerrainType.SAND, TerrainType.GRASS, TerrainType.WETLAND,
                        TerrainType.SWAMP, TerrainType.MEADOW, TerrainType.DIRT,
                    }:
                        continue
                    rise = tile.metadata.get("elevation", 0) - water.metadata.get("elevation", 0)
                    if rise <= 0.12:
                        banks[f"{x},{y}"] = {"x": x, "y": y, "walkable": tile.walkable,
                                                "threshold": 0.65 + max(0, rise)}
        state["banks"] = list(banks.values())
        state["chunk_count"] = len(world.chunks)
    target = {Season.SPRING: .55, Season.SUMMER: .2, Season.AUTUMN: .4, Season.WINTER: .25}[calendar.season]
    if calendar.weather == WeatherType.RAIN:
        target += calendar.weather_intensity * .65
    level = float(state.get("level", .3))
    level += max(-.04, min(.06, target - level))
    bridges = {(s.x, s.y) for s in world.structures.values()
               if s.structure_type.value == "BRIDGE" and s.completed and s.condition > 0}
    flooded = 0
    for bank in state["banks"]:
        tile = world.retrieve_tile(bank["x"], bank["y"])
        if tile is None:
            continue
        from app.application.services.editor_tools import local_weather
        local = local_weather(world, tile.x, tile.y, calendar, tick)
        local_target = {Season.SPRING: .55, Season.SUMMER: .2, Season.AUTUMN: .4, Season.WINTER: .25}[local.season]
        if local.weather == WeatherType.RAIN:
            local_target += local.weather_intensity * .65
        bank_level = float(bank.get("level", state.get("level", .3)))
        bank_level += max(-.04, min(.06, local_target - bank_level))
        bank["level"] = round(bank_level, 4)
        wet = bank_level > bank["threshold"]
        tile.metadata["flooded"] = wet
        tile.walkable = (not wet and bank["walkable"]) or (tile.x, tile.y) in bridges
        flooded += int(wet)
    state.update(tick=tick, level=round(level, 4), flooded_tiles=flooded)
