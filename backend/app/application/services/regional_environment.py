"""Checkpointed regional climate/soil; one chunk per update, no terrain replacement."""
from app.domain.models.calendar import get_calendar_control


def climate(world, tile):
    latitude = abs(2 * tile.y / max(1, world.height - 1) - 1)
    elevation = float(tile.metadata.get("elevation", .3))
    nearby_water = any(t.terrain.value in {"WATER", "OCEAN"} for t in world.get_neighbors(tile.x, tile.y, include_diagonals=True))
    cooling = -latitude * 8 - max(0, elevation-.3)*18
    region = "highlands" if elevation > .7 else "wetlands" if tile.metadata.get("moisture", .5) > .7 else "coastal" if nearby_water else "interior"
    return {"region": region, "temperature_offset_c": round(cooling*(.7 if nearby_water else 1), 2), "water_access": nearby_water}


def advance(world, tick, calendar):
    state = world.ecology.setdefault("regional_environment", {"cursor": 0, "last_tick": -1, "warnings": {}})
    if tick <= state["last_tick"] or tick % 12:
        return
    state["last_tick"] = tick
    keys = sorted(world.chunks)
    if not keys:
        return
    key = keys[state["cursor"] % len(keys)]
    state["cursor"] = (state["cursor"]+1) % len(keys)
    dry = wet = land = 0
    for tile in world.chunks[key].tiles.values():
        if not (0 <= tile.x < world.width and 0 <= tile.y < world.height):
            continue
        if tile.terrain.value in {"WATER", "OCEAN"}:
            continue
        land += 1
        profile = climate(world, tile)
        previous = tile.metadata.get("soil_tick", tick-12)
        elapsed = min(1.0, max(0, tick-previous)/get_calendar_control().ticks_per_day)
        temperature = calendar.temperature_c + profile["temperature_offset_c"]
        rain = calendar.weather.value == "RAIN"
        snow = float(tile.metadata.get("snow_cover", 0))
        precipitation = calendar.weather_intensity if rain or calendar.weather.value == "SNOW" else 0
        melt = min(snow, max(0, temperature)*.02*elapsed)
        snow = min(1, max(0, snow + (precipitation*.4*elapsed if temperature <= 0 else 0)-melt))
        moisture = float(tile.metadata.get("soil_moisture", tile.metadata.get("moisture", .5)))
        moisture += (precipitation*.5 if temperature > 0 else 0)*elapsed + melt
        moisture += (.08 if profile["water_access"] else 0)*elapsed
        moisture -= (.04 + max(0, temperature)*.004)*elapsed
        moisture = min(1, max(0, moisture))
        tile.metadata.update(regional_climate=profile, soil_tick=tick, soil_moisture=moisture, snow_cover=snow)
        if tick-tile.metadata.get("last_traffic_tick", tick) >= get_calendar_control().ticks_per_day:
            tile.metadata["foot_traffic"] = max(0, int(tile.metadata.get("foot_traffic", 0))-1)
        dry += moisture < .18
        wet += moisture > .9
    warning = "drought_watch" if land and dry/land > .4 else "saturated_soil" if land and wet/land > .4 else "normal"
    state["warnings"][key] = {"status": warning, "observed_tick": tick, "dry_tiles": dry, "wet_tiles": wet}


def growth_factor(tile):
    if tile is None or "soil_moisture" not in tile.metadata:
        return 1.0
    moisture = float(tile.metadata["soil_moisture"])
    return max(.05, min(1.2, moisture*2)) * (1-float(tile.metadata.get("snow_cover", 0))*.9)
