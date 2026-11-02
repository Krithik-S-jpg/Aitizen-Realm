"""Persistent wildlife homes, bounded songbirds and private field observations."""
from uuid import NAMESPACE_URL, uuid5

from app.domain.models.entity import Entity, EntityKind
from app.domain.models.calendar import DayPhase, Season, get_calendar_control
from app.domain.models.needs import NeedsState
from app.domain.models.resource import ResourceType
from app.domain.models.memory import Episode, EpisodeType


def _trees(world):
    return [r for r in world.resources.values() if r.resource_type == ResourceType.TREE and not r.depleted and r.growth >= .5]


def advance(world, tick, calendar):
    state = world.ecology
    if state.get("tick") == tick:
        return
    state["tick"] = tick
    homes = state.setdefault("homes", {})
    trees = _trees(world)
    day = tick // get_calendar_control().ticks_per_day
    if not state.get("birds_initialized") and trees:
        state["birds_initialized"] = True
        for tree in sorted(trees, key=lambda r: (r.x, r.y))[:4]:
            key = f"nest:{tree.x},{tree.y}"
            homes[key] = {"id": key, "kind": "nest", "species": "songbird", "x": tree.x, "y": tree.y,
                          "tree_id": str(tree.id), "status": "building", "progress": 0, "food_days": 0}
            bird = Entity(id=uuid5(NAMESPACE_URL, f"songbird:{world.seed}:{key}"), kind=EntityKind.ANIMAL,
                          name="Woodland songbird", x=tree.x, y=tree.y, needs=NeedsState(),
                          metadata={"species": "songbird", "habitat_id": key, "born_day": day, "state": "nesting"})
            world.entities[str(bird.id)] = bird
    for animal in list(world.entities.values()):
        if not animal.active or animal.kind != EntityKind.ANIMAL or animal.metadata.get("marine") or animal.metadata.get("cave_animal"):
            continue
        species = animal.metadata.get("species", "")
        if species != "songbird":
            kind = "burrow" if species == "rabbit" else "den" if species in {"wolf", "fox", "bear"} else "resting_ground"
            hx, hy = int(animal.metadata.get("home_x", animal.x)), int(animal.metadata.get("home_y", animal.y))
            key = f"{species}:{hx},{hy}"
            if key not in homes and len(homes) < 256:
                homes[key] = {"id": key, "kind": kind, "species": species, "x": hx, "y": hy, "status": "occupied"}
            animal.metadata["habitat_id"] = key
            animal.metadata["habitat"] = homes.get(key, {})
            continue
        nearby = any(e.active and e.kind == EntityKind.AGENT and e.distance_squared_to(animal.x, animal.y) <= 900 for e in world.entities.values())
        if tick % (2 if nearby else 8):
            continue
        home = homes.get(animal.metadata.get("habitat_id"), {})
        tree = world.resources.get(home.get("tree_id"))
        if not tree or tree.depleted or tree.growth < .5:
            if home:
                home.update(status="abandoned", eggs=0)
            choices = [t for t in trees if f"nest:{t.x},{t.y}" not in homes]
            if not choices or len(homes) >= 256:
                animal.metadata.update(state="displaced", altitude=0, behavior_reason="Tree cover was lost; no vacant nesting tree is available.")
                continue
            tree = min(choices, key=lambda r: animal.distance_squared_to(r.x, r.y))
            key = f"nest:{tree.x},{tree.y}"
            home = {"id": key, "kind": "nest", "species": species, "x": tree.x, "y": tree.y,
                    "tree_id": str(tree.id), "status": "building", "progress": 0, "food_days": 0}
            homes[key] = home
            animal.metadata["habitat_id"] = key
        animal.metadata["age_days"] = day - int(animal.metadata.get("born_day", day))
        animal.metadata["habitat"] = home
        if animal.metadata["age_days"] >= 720:
            animal.active = False
            animal.metadata["death_reason"] = "old_age"
            continue
        animal.metadata["life_stage"] = "juvenile" if animal.metadata.get("parent_id") and animal.metadata["age_days"] < 3 else "adult"
        target = (home["x"], home["y"])
        from app.application.services.editor_tools import local_weather
        local = local_weather(world, animal.x, animal.y, calendar, tick)
        resting = calendar.phase == DayPhase.NIGHT or local.weather_intensity >= .65
        food = None
        drink = False
        if not resting and animal.metadata["life_stage"] == "adult" and animal.needs.hunger > 15:
            foods = [r for r in world.resources.values() if not r.depleted and r.resource_type in {ResourceType.PLANT, ResourceType.BUSH, ResourceType.HERB} and r.quantity >= .5 and animal.distance_squared_to(r.x, r.y) <= 144]
            farms = [s for s in world.structures.values() if s.completed and s.crop_food >= .5 and animal.distance_squared_to(s.x, s.y) <= 144]
            food = min(foods + farms, key=lambda r: animal.distance_squared_to(r.x, r.y), default=None)
            if food:
                target = (food.x, food.y)
        if animal.needs.thirst > 35:
            water = [world.retrieve_tile(x, y) for x in range(max(0, animal.x-10), min(world.width, animal.x+11)) for y in range(max(0, animal.y-10), min(world.height, animal.y+11))]
            source = min((t for t in water if t and t.terrain.value == "WATER"), key=lambda t: animal.distance_squared_to(t.x, t.y), default=None)
            if source:
                target, drink, food = (source.x, source.y), True, None
        if (animal.x, animal.y) != target:
            # Flight ignores ground obstructions but never teleports to the target.
            if animal.x != target[0]:
                animal.x += (target[0] > animal.x) - (target[0] < animal.x)
            else:
                animal.y += (target[1] > animal.y) - (target[1] < animal.y)
            animal.metadata.update(state="fly", altitude=35, behavior_reason="Flying to food or a nesting tree.")
            continue
        animal.metadata.update(state="perch" if resting else "nesting", altitude=25 if target == (home["x"], home["y"]) else 0)
        if resting:
            animal.needs.rest(5)
        if drink:
            animal.needs.thirst = max(0, animal.needs.thirst - 30)
            animal.metadata.update(state="drink", altitude=0)
        elif food:
            if hasattr(food, "crop_food"):
                food.crop_food -= .5
            else:
                food.quantity -= .5
            animal.needs.hunger = max(0, animal.needs.hunger - 20)
            animal.metadata.update(state="feed", altitude=0, last_fed_day=day)
        elif not resting:
            home["progress"] = min(4, home.get("progress", 0) + 1)
            home["status"] = "occupied" if home["progress"] == 4 else "building"
            if animal.metadata["life_stage"] == "adult" and home.get("last_brood_day") != day and animal.metadata.get("last_fed_day", -10) >= day - 1:
                home["last_brood_day"] = day
                home["food_days"] = home.get("food_days", 0) + 1
                if calendar.season == Season.SPRING and home["progress"] == 4 and not home.get("hatched"):
                    home["eggs"] = 1
                    birds = sum(e.active and e.metadata.get("species") == "songbird" for e in world.entities.values())
                    if home["food_days"] >= 3 and birds < 16:
                        chick = Entity(kind=EntityKind.ANIMAL, name="Songbird fledgling", x=animal.x, y=animal.y,
                            needs=NeedsState(), metadata={"species": "songbird", "habitat_id": home["id"],
                            "born_day": day, "parent_id": str(animal.id), "life_stage": "juvenile", "state": "nesting"})
                        world.entities[str(chick.id)] = chick
                        home.update(eggs=0, hatched=True)
            for chick in world.entities.values():
                if chick.active and chick.metadata.get("parent_id") == str(animal.id) and chick.metadata.get("life_stage") == "juvenile" and animal.metadata.get("last_fed_day", -10) >= day - 1:
                    chick.needs.hunger = max(0, chick.needs.hunger - 10)


def observe(world, citizen, tick):
    if citizen.kind != EntityKind.AGENT or citizen.metadata.get("in_cave") or citizen.metadata.get("underwater"):
        return
    records = citizen.metadata.setdefault("wildlife_journal", {})
    for home in world.ecology.get("homes", {}).values():
        if citizen.distance_squared_to(home["x"], home["y"]) > citizen.perception_radius ** 2:
            continue
        key = home["id"]
        first = records.get(key, {}).get("first_seen_tick", tick)
        if key not in records:
            episodes = world.episodes.setdefault(str(citizen.id), [])
            episodes.append(Episode(entity_id=citizen.id, episode_type=EpisodeType.DISCOVERY,
                tick=tick, x=home["x"], y=home["y"], importance=.75,
                summary=f"Discovered a {home['species']} {home['kind'].replace('_', ' ')}.", details={"habitat_id": key}))
            del episodes[:-200]
        records[key] = {**home, "first_seen_tick": first, "last_seen_tick": tick, "observer": citizen.name}
    for animal in world.entities.values():
        if not animal.active or animal.kind != EntityKind.ANIMAL or not animal.metadata.get("migration_target") or animal.metadata.get("state") != "migrate":
            continue
        if citizen.distance_squared_to(animal.x, animal.y) <= citizen.perception_radius ** 2:
            key = f"route:{animal.id}"
            record = records.setdefault(key, {"kind": "migration_sightings", "species": animal.metadata.get("species"), "observer": citizen.name, "first_seen_tick": tick, "points": []})
            point = [animal.x, animal.y]
            if not record["points"] or record["points"][-1] != point:
                record["points"] = (record["points"] + [point])[-16:]
            record.update(id=key, x=animal.x, y=animal.y, last_seen_tick=tick)


def journal(world):
    return [record for e in world.entities.values() if e.kind == EntityKind.AGENT
            for record in e.metadata.get("wildlife_journal", {}).values()]
