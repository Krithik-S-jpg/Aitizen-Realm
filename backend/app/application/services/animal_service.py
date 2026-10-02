"""Species-specific deterministic wildlife behavior."""

import json
from collections import deque
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.domain.interfaces.world_repository import IWorldRepository
from app.application.services.danger_memory import remember_attack, sheltered
from app.domain.models.calendar import (
    DayPhase,
    Season,
    calendar_at_tick,
    get_calendar_control,
)
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.species import SpeciesLifeHistory
from app.domain.models.structure import StructureType
from app.domain.models.world import TerrainType, World


class AnimalService:
    """Runs animal survival, feeding, social, and predator-prey behavior."""

    PROFILES: dict[str, dict[str, Any]] = {
        "deer": {
            "diet": {ResourceType.PLANT, ResourceType.BUSH, ResourceType.HERB},
            "active": {DayPhase.DAWN, DayPhase.DAY, DayPhase.DUSK},
            "habitats": {TerrainType.FOREST, TerrainType.GRASS, TerrainType.MEADOW},
            "flight_radius": 7,
            "social": True,
            "water_search": 10,
        },
        "rabbit": {
            "diet": {ResourceType.PLANT, ResourceType.HERB},
            "active": {DayPhase.DAWN, DayPhase.DUSK, DayPhase.NIGHT},
            "habitats": {TerrainType.GRASS, TerrainType.MEADOW, TerrainType.SAVANNA},
            "flight_radius": 8,
            "social": True,
            "water_search": 7,
        },
        "boar": {
            "diet": {
                ResourceType.PLANT,
                ResourceType.BUSH,
                ResourceType.HERB,
                ResourceType.MUSHROOM,
            },
            "active": {DayPhase.DUSK, DayPhase.NIGHT, DayPhase.DAWN},
            "habitats": {TerrainType.FOREST, TerrainType.WETLAND, TerrainType.SWAMP},
            "flight_radius": 5,
            "social": True,
            "water_search": 9,
        },
        "wolf": {
            "diet": set(),
            "active": {DayPhase.DUSK, DayPhase.NIGHT, DayPhase.DAWN},
            "habitats": {TerrainType.FOREST, TerrainType.MOUNTAIN, TerrainType.TUNDRA},
            "flight_radius": 0,
            "social": True,
            "water_search": 12,
        },
        "fox": {
            "diet": set(),
            "active": {DayPhase.DUSK, DayPhase.NIGHT, DayPhase.DAWN},
            "habitats": {TerrainType.FOREST, TerrainType.GRASS, TerrainType.TUNDRA},
            "flight_radius": 5,
            "social": False,
            "water_search": 9,
        },
        "bear": {
            "diet": {
                ResourceType.BUSH,
                ResourceType.MUSHROOM,
                ResourceType.PLANT,
            },
            "active": {DayPhase.DAWN, DayPhase.DAY, DayPhase.DUSK},
            "habitats": {TerrainType.FOREST, TerrainType.MOUNTAIN},
            "flight_radius": 0,
            "social": False,
            "water_search": 12,
        },
        "goat": {
            "diet": {ResourceType.PLANT, ResourceType.HERB},
            "active": {DayPhase.DAWN, DayPhase.DAY, DayPhase.DUSK},
            "habitats": {
                TerrainType.MOUNTAIN,
                TerrainType.STONE,
                TerrainType.SAVANNA,
            },
            "flight_radius": 6,
            "social": True,
            "water_search": 10,
        },
        "duck": {
            "diet": {ResourceType.REEDS, ResourceType.LILY, ResourceType.PLANT},
            "active": {DayPhase.DAWN, DayPhase.DAY, DayPhase.DUSK},
            "habitats": {TerrainType.WETLAND, TerrainType.SWAMP, TerrainType.GRASS},
            "flight_radius": 6,
            "social": True,
            "water_search": 5,
        },
    }
    WATER_TERRAINS = {TerrainType.WATER, TerrainType.OCEAN, TerrainType.SWAMP}

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes wildlife behavior against the shared world store."""
        self._repository = repository
        config_path = Path(__file__).resolve().parents[2] / "config" / "species.json"
        raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        self._life_history = {
            species: SpeciesLifeHistory.model_validate(values)
            for species, values in raw.items()
        }
        self._routines = json.loads(
            config_path.with_name("animal_routines.json").read_text(encoding="utf-8")
        )

    def advance_all(self, tick: int) -> None:
        """Advances each animal from its species and survival pressure."""
        world = self._repository.get()
        if world is None:
            return
        calendar = calendar_at_tick(tick)
        for citizen in world.entities.values():
            if citizen.kind == EntityKind.AGENT:
                citizen.metadata["emotion_tick"] = tick
        self._finalize_deaths(world, tick)
        if tick > 0 and tick % get_calendar_control().ticks_per_day == 0:
            self._advance_life_cycles(world, tick, calendar.season)
        animals = sorted(
            (
                entity
                for entity in world.entities.values()
                if entity.active and entity.kind == EntityKind.ANIMAL
            ),
            key=lambda item: str(item.id),
        )
        for animal in animals:
            if not animal.active:
                continue  # A predator may have killed this animal earlier this tick.
            animal.metadata["weather"] = calendar.weather.value.lower()
            animal.metadata["weather_intensity"] = calendar.weather_intensity
            animal.metadata["ambient_temperature_c"] = calendar.feels_like_c
            cadence = min(2, max(1, int(animal.metadata.get("move_cadence", 1))))
            if tick % cadence != animal.id.int % cadence:
                continue
            self._decide(world, animal, calendar.phase, calendar.season, tick)

    def _advance_life_cycles(self, world: World, tick: int, season: Season) -> None:
        """Advances age, pregnancy, births, and density-dependent population."""
        ticks_per_day = get_calendar_control().ticks_per_day
        animals = sorted(
            (
                entity
                for entity in world.entities.values()
                if entity.active and entity.kind == EntityKind.ANIMAL
            ),
            key=lambda item: str(item.id),
        )
        for animal in animals:
            species = str(animal.metadata.get("species", "rabbit"))
            history = self._life_history.get(species)
            if history is None:
                continue
            age_ticks = int(animal.metadata.get("age_ticks", 0)) + 24
            animal.metadata["age_ticks"] = age_ticks
            age_days = age_ticks // 24
            animal.metadata["age_days"] = age_days
            animal.metadata["age_stage"] = self._age_stage(age_days, history)
            maximum_age = int(
                animal.metadata.setdefault(
                    "maximum_age_days",
                    history.lifespan_days
                    + (animal.id.int % max(2, history.lifespan_days // 5))
                    - history.lifespan_days // 10,
                )
            )
            if age_days >= maximum_age:
                self._die(world, animal, tick, "old_age", history.meat_yield * 0.7)
                continue
            if animal.metadata["age_stage"] != "adult":
                continue
            pregnant_since = animal.metadata.get("pregnant_since_tick")
            if pregnant_since is not None:
                if tick - int(pregnant_since) >= history.gestation_days * ticks_per_day:
                    self._give_birth(world, animal, species, history, tick)
                continue
            if (
                animal.metadata.get("sex") != "female"
                or season not in history.breeding_seasons
                or animal.needs is None
                or animal.needs.health < 75
                or animal.needs.hunger > 35
                or animal.needs.energy < 55
                or tick - int(animal.metadata.get("last_birth_tick", -100_000))
                < history.gestation_days * ticks_per_day
                or self._local_population(
                    world, animal, species, history.territory_radius
                )
                >= self._local_capacity(world, animal, species, history)
            ):
                continue
            mate = next(
                (
                    other
                    for other in animals
                    if other.id != animal.id
                    and str(other.metadata.get("species", "")) == species
                    and other.metadata.get("sex") == "male"
                    and other.metadata.get("age_stage") == "adult"
                    and animal.distance_squared_to(other.x, other.y)
                    <= history.territory_radius**2
                    and other.needs is not None
                    and other.needs.health >= 65
                ),
                None,
            )
            if mate is not None:
                animal.metadata["pregnant_since_tick"] = tick
                animal.metadata["mate_id"] = str(mate.id)
                self._set_state(animal, "nest", tick, str(mate.id))

    def _give_birth(
        self,
        world: World,
        mother: Entity,
        species: str,
        history: SpeciesLifeHistory,
        tick: int,
    ) -> None:
        """Creates bounded offspring only while local carrying capacity remains."""
        capacity = self._local_capacity(world, mother, species, history)
        population = self._local_population(
            world, mother, species, history.territory_radius
        )
        available = max(0, capacity - population)
        desired = history.litter_min + (
            (mother.id.int + tick) % (history.litter_max - history.litter_min + 1)
        )
        births = min(available, desired)
        for index in range(births):
            position = self._birth_position(world, mother, index)
            if position is None:
                break
            child_id = uuid5(
                NAMESPACE_URL,
                f"aitizen-realm:birth:{mother.id}:{tick}:{index}",
            )
            child = Entity(
                id=child_id,
                kind=EntityKind.ANIMAL,
                name=f"Young {species.title()}",
                x=position[0],
                y=position[1],
                perception_radius=max(3, mother.perception_radius - 1),
                tags={"wildlife", species, "offspring"},
                needs=mother.needs.model_copy(
                    update={
                        "hunger": 5.0,
                        "thirst": 5.0,
                        "energy": 85.0,
                        "health": 100.0,
                    }
                )
                if mother.needs is not None
                else None,
                metadata={
                    "species": species,
                    "sex": "female" if child_id.int % 2 == 0 else "male",
                    "age_ticks": 0,
                    "age_days": 0,
                    "age_stage": "young",
                    "birth_tick": tick,
                    "mother_id": str(mother.id),
                    "father_id": str(mother.metadata.get("mate_id", "")),
                    "home_x": mother.x,
                    "home_y": mother.y,
                    "herd_id": mother.metadata.get(
                        "herd_id", f"{species}:{mother.x // 8}:{mother.y // 8}"
                    ),
                    "state": "follow_parent",
                    "move_cadence": 2,
                },
            )
            world.entities[str(child.id)] = child
        mother.metadata.pop("pregnant_since_tick", None)
        mother.metadata["last_birth_tick"] = tick
        mother.metadata["offspring_count"] = (
            int(mother.metadata.get("offspring_count", 0)) + births
        )
        if mother.needs is not None:
            mother.needs.energy = max(20.0, mother.needs.energy - births * 9.0)
            mother.needs.hunger = min(100.0, mother.needs.hunger + births * 5.0)
        self._set_state(mother, "care_young", tick)

    def _finalize_deaths(self, world: World, tick: int) -> None:
        """Turns physiological deaths into persistent ecological consequences."""
        for animal in list(world.entities.values()):
            if (
                animal.kind == EntityKind.ANIMAL
                and not animal.active
                and "death_tick" not in animal.metadata
            ):
                species = str(animal.metadata.get("species", "rabbit"))
                history = self._life_history.get(species)
                self._die(
                    world,
                    animal,
                    tick,
                    "starvation_or_exposure",
                    history.meat_yield * 0.65 if history is not None else 3.0,
                )

    def _die(
        self,
        world: World,
        animal: Entity,
        tick: int,
        cause: str,
        remains: float,
    ) -> None:
        """Ends one life once and adds finite, decaying remains to the world."""
        if "death_tick" in animal.metadata:
            return
        animal.active = False
        animal.metadata.update(
            {"death_tick": tick, "death_cause": cause, "state": "dead"}
        )
        if remains > 0:
            carcass = ResourceNode(
                resource_type=ResourceType.CARCASS,
                x=animal.x,
                y=animal.y,
                quantity=remains,
                capacity=remains,
                visual_state="fresh",
                state_changed_tick=tick,
            )
            world.add_resource(carcass)

    @staticmethod
    def _age_stage(age_days: int, history: SpeciesLifeHistory) -> str:
        if age_days < max(1, history.maturity_days // 3):
            return "young"
        if age_days < history.maturity_days:
            return "juvenile"
        if age_days >= int(history.lifespan_days * 0.8):
            return "elder"
        return "adult"

    def _decide(
        self,
        world: World,
        animal: Entity,
        phase: DayPhase,
        season: Season,
        tick: int,
    ) -> None:
        species = str(animal.metadata.get("species", "rabbit"))
        profile = self.PROFILES.get(species, self.PROFILES["rabbit"])
        animal.metadata.setdefault("home_x", animal.x)
        animal.metadata.setdefault("home_y", animal.y)
        needs = animal.needs
        routine = self._routines.get(species, self._routines["rabbit"])
        # Stable individual differences, persisted in the animal's own state.
        appetite = float(
            animal.metadata.setdefault("feeding_threshold", 18 + animal.id.int % 11)
        )
        animal.metadata["lifestyle"] = routine["description"]
        if self._attack_citizen(world, animal, tick):
            return
        # Predators and dehydration interrupt comfort/weather routines.
        if species not in {"wolf", "bear"} and self._flee(world, animal, profile, tick):
            return
        if needs is not None and needs.thirst >= 70:
            if self._drink_or_seek_water(world, animal, profile, tick):
                return
        # Water affinity is a continuing habitat need, not only a spawn rule.
        # Fear above can still drive a duck inland; it returns once safe.
        if species == "duck" and not self._terrain_near(
            world, animal.x, animal.y, {TerrainType.WATER}, 3
        ):
            shoreline = self._nearest_terrain(
                world, animal, {TerrainType.WATER}, int(profile["water_search"])
            )
            if shoreline is not None and self._step_toward(
                world, animal, shoreline.x, shoreline.y, "seek_water", tick
            ):
                animal.metadata["behavior_reason"] = "Returning to shoreline habitat after straying inland."
                animal.metadata.update({"home_x": animal.x, "home_y": animal.y})
                return
        severe_weather = (
            float(animal.metadata.get("weather_intensity", 0.0)) >= 0.58
            or float(animal.metadata.get("ambient_temperature_c", 18.0)) < -5.0
        )
        if severe_weather and species not in {"duck", "goat", "bear"}:
            shelter = self._nearest_terrain(
                world,
                animal,
                {TerrainType.FOREST},
                int(profile["water_search"]),
            )
            if (
                shelter is not None
                and animal.distance_squared_to(shelter.x, shelter.y) > 2
            ):
                if self._step_toward(
                    world, animal, shelter.x, shelter.y, "seek_weather_shelter", tick
                ):
                    return
            elif shelter is not None:
                if needs is not None:
                    needs.rest(2.0)
                self._set_state(animal, "shelter_weather", tick)
                return
        if species not in {"wolf", "bear"} and self._flee(world, animal, profile, tick):
            return
        if needs is not None and needs.energy < 24.0:
            needs.rest(5.5)
            self._set_state(animal, "rest", tick)
            return
        if needs is not None and needs.thirst > 32.0:
            if self._drink_or_seek_water(world, animal, profile, tick):
                return
        if (
            species == "bear"
            and season == Season.WINTER
            and (needs is None or needs.hunger < 72.0)
        ):
            if needs is not None:
                needs.rest(4.5)
            self._set_state(animal, "sleep", tick)
            animal.metadata["seasonal_state"] = "hibernating"
            return
        animal.metadata["seasonal_state"] = "active"
        if phase not in profile["active"] and (needs is None or needs.hunger < 58.0):
            home_x = int(animal.metadata["home_x"])
            home_y = int(animal.metadata["home_y"])
            home = world.retrieve_tile(home_x, home_y)
            if (
                home is None
                or home.terrain not in profile["habitats"]
                or not self._can_enter(world, home_x, home_y)
            ):
                habitat = self._nearest_terrain(
                    world, animal, profile["habitats"], int(profile["water_search"])
                )
                if habitat is not None and self._can_enter(world, habitat.x, habitat.y):
                    home_x, home_y = habitat.x, habitat.y
                    animal.metadata.update({"home_x": home_x, "home_y": home_y})
            if animal.distance_squared_to(home_x, home_y) > 4 and self._step_toward(
                world, animal, home_x, home_y, "return_home", tick
            ):
                return
            if needs is not None:
                needs.rest(3.0)
            self._set_state(animal, "sleep", tick)
            return
        if species in {"wolf", "fox"}:
            if needs is None or needs.hunger > appetite:
                if self._scavenge(world, animal, tick) or self._hunt(
                    world, animal, tick
                ):
                    return
            if (
                needs is not None
                and needs.hunger > 52.0
                and self._migrate(world, animal, profile, tick)
            ):
                return
        elif needs is not None and needs.hunger > appetite:
            if species == "bear" and self._scavenge(world, animal, tick):
                return
            if self._forage(world, animal, profile, tick):
                return
            if species == "boar" and self._root_for_food(world, animal, tick):
                return
            if needs.hunger > 52.0 and self._migrate(world, animal, profile, tick):
                return
        if animal.metadata.get("age_stage") == "young":
            mother = world.entities.get(str(animal.metadata.get("mother_id", "")))
            if (
                mother is not None
                and mother.active
                and animal.distance_squared_to(mother.x, mother.y) > 4
                and self._step_toward(
                    world, animal, mother.x, mother.y, "follow_parent", tick
                )
            ):
                return
        if bool(profile["social"]) and self._regroup(world, animal, species, tick):
            return
        # Comfort behavior occurs only after danger, thirst, feeding and family.
        # It is staggered per individual, bounded, and never replaces urgent needs.
        if needs is not None and needs.hunger < 35 and needs.thirst < 32:
            interval = int(routine["comfort_interval"])
            if (tick + animal.id.int) % interval == 0:
                needs.rest(float(routine["rest_gain"]))
                self._set_state(animal, str(routine["comfort_action"]), tick)
                animal.metadata["behavior_reason"] = routine["description"]
                return
        self._patrol_habitat(world, animal, profile, tick)

    def _attack_citizen(self, world: World, animal: Entity, tick: int) -> bool:
        species = str(animal.metadata.get("species", ""))
        if species not in {"wolf", "bear", "boar"} or animal.metadata.get("age_stage") == "young":
            return False
        if tick - int(animal.metadata.get("last_citizen_attack_tick", -100)) < 4:
            return False
        hungry = animal.needs is not None and animal.needs.hunger >= 60
        # Wolves hunt when hungry; bears/boars defend close personal space.
        radius = 4 if species == "wolf" and hungry else 1
        if species == "wolf" and not hungry:
            return False
        targets = [e for e in world.entities.values() if e.active and e.kind == EntityKind.AGENT
                   and e.needs is not None and not sheltered(world, e)
                   and animal.distance_squared_to(e.x, e.y) <= radius ** 2]
        if not targets:
            return False
        target = min(targets, key=lambda e: (animal.distance_squared_to(e.x, e.y), str(e.id)))
        if animal.distance_squared_to(target.x, target.y) > 2:
            return self._step_toward(world, animal, target.x, target.y, "hunt", tick)
        damage = {"wolf": 12, "bear": 18, "boar": 8}[species]
        target.needs.health = max(0, target.needs.health - damage)
        target.metadata["last_attacked_tick"] = tick
        animal.metadata["last_citizen_attack_tick"] = tick
        self._set_state(animal, "attack", tick, str(target.id))
        animal.metadata["behavior_reason"] = "Hunting for food" if species == "wolf" else "Defending personal space"
        remember_attack(world, animal, target, tick)
        if target.needs.health == 0:
            target.active = False
            target.metadata.update(state="dead", death_cause="wildlife_attack", died_at_tick=tick)
            if species == "wolf" and animal.needs is not None:
                animal.needs.eat(38)
                self._set_state(animal, "feed", tick, str(target.id))
        return True

    def _hunt(self, world: World, hunter: Entity, tick: int) -> bool:
        hunter_species = str(hunter.metadata.get("species", "wolf"))
        prey_species = (
            {"rabbit", "deer"} if hunter_species == "wolf" else {"rabbit", "duck"}
        )
        hunting_radius = 144 if hunter_species == "wolf" else 81
        prey = [
            entity
            for entity in world.entities.values()
            if entity.active
            and entity.kind == EntityKind.ANIMAL
            and str(entity.metadata.get("species", "")) in prey_species
            and hunter.distance_squared_to(entity.x, entity.y) <= hunting_radius
        ]
        if not prey:
            return False
        target = min(
            prey,
            key=lambda item: (
                hunter.distance_squared_to(item.x, item.y),
                str(item.id),
            ),
        )
        if hunter.distance_squared_to(target.x, target.y) <= 2:
            self._consume_prey(world, hunter, target, tick)
            return True
        moved = self._step_toward(
            world, hunter, target.x, target.y, "hunt", tick, allow_diagonal=True
        )
        if moved and hunter.distance_squared_to(target.x, target.y) <= 2:
            self._consume_prey(world, hunter, target, tick)
        return moved

    def _scavenge(self, world: World, animal: Entity, tick: int) -> bool:
        """Consumes nearby finite remains before creating another prey death."""
        carcasses = self._nearby_resources(
            world, animal, {ResourceType.CARCASS}, radius=8
        )
        if not carcasses:
            return False
        carcass = carcasses[0]
        if animal.distance_squared_to(carcass.x, carcass.y) <= 2:
            consumed = carcass.harvest(min(2.0, carcass.quantity))
            if animal.needs is not None:
                animal.needs.eat(max(2.0, consumed * 7.0))
                animal.needs.energy = min(100.0, animal.needs.energy + consumed)
            animal.metadata["scavenged"] = round(
                float(animal.metadata.get("scavenged", 0.0)) + consumed, 2
            )
            self._set_state(animal, "feed", tick, str(carcass.id))
            return True
        return self._step_toward(world, animal, carcass.x, carcass.y, "forage", tick)

    def _consume_prey(
        self, world: World, hunter: Entity, target: Entity, tick: int
    ) -> None:
        """Completes a close-range predator-prey interaction."""
        species = str(target.metadata.get("species", "rabbit"))
        history = self._life_history.get(species)
        remains = history.meat_yield * 0.35 if history is not None else 2.0
        self._die(world, target, tick, "predation", remains)
        target.metadata["killed_by"] = str(hunter.id)
        self._set_state(hunter, "feed", tick, str(target.id))
        hunter.metadata["meals"] = int(hunter.metadata.get("meals", 0)) + 1
        if hunter.needs is not None:
            hunter.needs.eat(38.0)
            hunter.needs.energy = min(100.0, hunter.needs.energy + 7.0)

    def _migrate(
        self, world: World, animal: Entity, profile: dict[str, Any], tick: int
    ) -> bool:
        """Moves toward a higher-quality habitat patch when local needs fail."""
        species = str(animal.metadata.get("species", "rabbit"))
        history = self._life_history.get(species)
        radius = history.territory_radius * 2 if history is not None else 16
        accepted_food: set[ResourceType] = profile["diet"]
        candidates: list[tuple[float, int, int]] = []
        for x in range(animal.x - radius, animal.x + radius + 1, 2):
            for y in range(animal.y - radius, animal.y + radius + 1, 2):
                tile = world.retrieve_tile(x, y)
                if (
                    tile is None
                    or not tile.walkable
                    or tile.terrain not in profile["habitats"]
                ):
                    continue
                food = sum(
                    min(resource.quantity, 10.0)
                    for resource in world.resources.values()
                    if not resource.depleted
                    and resource.resource_type in accepted_food
                    and (resource.x - x) ** 2 + (resource.y - y) ** 2 <= 25
                )
                prey = sum(
                    1
                    for other in world.entities.values()
                    if other.active
                    and other.kind == EntityKind.ANIMAL
                    and str(other.metadata.get("species", ""))
                    in ({"rabbit", "deer"} if species == "wolf" else {"rabbit", "duck"})
                    and (other.x - x) ** 2 + (other.y - y) ** 2 <= 49
                )
                water = (
                    1.0
                    if self._terrain_near(world, x, y, self.WATER_TERRAINS, 4)
                    else 0.0
                )
                crowding = sum(
                    1
                    for other in world.entities.values()
                    if other.active
                    and other.kind == EntityKind.ANIMAL
                    and str(other.metadata.get("species", "")) == species
                    and (other.x - x) ** 2 + (other.y - y) ** 2 <= 36
                )
                distance = animal.distance_squared_to(x, y) ** 0.5
                score = (
                    food + prey * 8.0 + water * 4.0 - crowding * 2.5 - distance * 0.08
                )
                candidates.append((score, x, y))
        if not candidates:
            return False
        _, x, y = max(candidates, key=lambda item: (item[0], -item[1], -item[2]))
        if (x, y) == (animal.x, animal.y):
            return False
        animal.metadata["migration_target"] = [x, y]
        animal.metadata["migration_reason"] = "food_and_water_pressure"
        return self._step_toward(world, animal, x, y, "migrate", tick)

    def _flee(
        self, world: World, animal: Entity, profile: dict[str, Any], tick: int
    ) -> bool:
        radius = int(profile["flight_radius"])
        threats = [
            entity
            for entity in world.entities.values()
            if entity.active
            and entity.id != animal.id
            and (
                entity.kind == EntityKind.AGENT
                or str(entity.metadata.get("species", "")) in {"wolf", "fox", "bear"}
            )
            and animal.distance_squared_to(entity.x, entity.y) <= radius**2
        ]
        if not threats:
            return False
        threat = min(
            threats, key=lambda item: animal.distance_squared_to(item.x, item.y)
        )
        if animal.needs is not None:
            animal.needs.safety = max(0.0, animal.needs.safety - 1.5)
            animal.needs.energy = max(0.0, animal.needs.energy - 0.8)
        return self._step_toward(
            world,
            animal,
            animal.x + (animal.x - threat.x) * 2,
            animal.y + (animal.y - threat.y) * 2,
            "flee",
            tick,
            allow_diagonal=True,
        )

    def _forage(
        self, world: World, animal: Entity, profile: dict[str, Any], tick: int
    ) -> bool:
        resources = self._nearby_resources(world, animal, profile["diet"], radius=7)
        if not resources:
            tile = world.retrieve_tile(animal.x, animal.y)
            if (
                tile is not None
                and tile.terrain
                in {TerrainType.GRASS, TerrainType.MEADOW, TerrainType.SAVANNA}
                and (animal.id.int + tick) % 3 == 0
            ):
                last_tick = int(tile.metadata.get("last_grazed_tick", tick))
                pressure = max(
                    0.0,
                    float(tile.metadata.get("grazing_pressure", 0.0))
                    - max(0, tick - last_tick) * 0.002,
                )
                if pressure >= 0.96:
                    return False
                consumed = min(0.04, 1.0 - pressure)
                if animal.needs is not None:
                    animal.needs.eat(consumed * 75.0)
                tile.metadata["grazing_pressure"] = round(pressure + consumed, 3)
                tile.metadata["last_grazed_tick"] = tick
                self._set_state(animal, "graze", tick)
                return True
            return False
        food = resources[0]
        if animal.distance_squared_to(food.x, food.y) <= 2:
            consumed = food.harvest(min(0.55, food.quantity))
            if animal.needs is not None:
                animal.needs.eat(max(1.0, consumed * 6.0))
            self._set_state(animal, "graze", tick, str(food.id))
            animal.metadata["foraged"] = round(
                float(animal.metadata.get("foraged", 0.0)) + consumed, 2
            )
            return True
        return self._step_toward(world, animal, food.x, food.y, "forage", tick)

    def _root_for_food(self, world: World, animal: Entity, tick: int) -> bool:
        tile = world.retrieve_tile(animal.x, animal.y)
        if tile is None or tile.terrain not in {
            TerrainType.DIRT,
            TerrainType.FOREST,
            TerrainType.SAVANNA,
        }:
            return False
        if (animal.id.int + tick) % 4 != 0:
            return False
        if animal.needs is not None:
            animal.needs.eat(4.0)
        self._set_state(animal, "root", tick)
        animal.metadata["rooted_patches"] = (
            int(animal.metadata.get("rooted_patches", 0)) + 1
        )
        return True

    def _drink_or_seek_water(
        self, world: World, animal: Entity, profile: dict[str, Any], tick: int
    ) -> bool:
        water = self._nearest_terrain(
            world, animal, self.WATER_TERRAINS, int(profile["water_search"])
        )
        if water is None:
            return False
        if animal.distance_squared_to(water.x, water.y) <= 2:
            if animal.needs is not None:
                animal.needs.drink(36.0)
            self._set_state(animal, "drink", tick)
            return True
        return self._step_toward(world, animal, water.x, water.y, "seek_water", tick)

    def _regroup(self, world: World, animal: Entity, species: str, tick: int) -> bool:
        companions = [
            entity
            for entity in world.entities.values()
            if entity.active
            and entity.id != animal.id
            and entity.kind == EntityKind.ANIMAL
            and str(entity.metadata.get("species", "")) == species
            and 25 < animal.distance_squared_to(entity.x, entity.y) <= 100
        ]
        if not companions:
            return False
        companion = min(
            companions, key=lambda item: animal.distance_squared_to(item.x, item.y)
        )
        return self._step_toward(
            world, animal, companion.x, companion.y, "regroup", tick
        )

    def _patrol_habitat(
        self, world: World, animal: Entity, profile: dict[str, Any], tick: int
    ) -> None:
        home_x = int(animal.metadata.get("home_x", animal.x))
        home_y = int(animal.metadata.get("home_y", animal.y))
        if animal.distance_squared_to(home_x, home_y) > 100:
            self._step_toward(world, animal, home_x, home_y, "return_home", tick)
            return
        destination = animal.metadata.get("patrol_destination")
        if destination is not None and (animal.x, animal.y) != tuple(destination):
            if self._step_toward(
                world, animal, int(destination[0]), int(destination[1]), "patrol", tick
            ):
                return
        destinations = [
            (x, y)
            for x in range(home_x - 8, home_x + 9)
            for y in range(home_y - 8, home_y + 9)
            if 9 <= animal.distance_squared_to(x, y) <= 100
            and self._can_enter(world, x, y)
            and self._terrain_at(world, (x, y)) in profile["habitats"]
            and (
                animal.metadata.get("species") != "duck"
                or any(
                    (water := world.retrieve_tile(x + dx, y + dy)) is not None
                    and water.terrain
                    in {TerrainType.WATER, TerrainType.WETLAND, TerrainType.SWAMP}
                    for dx in range(-3, 4)
                    for dy in range(-3, 4)
                )
            )
        ]
        if destinations:
            destination = destinations[(animal.id.int + tick // 4) % len(destinations)]
            animal.metadata["patrol_destination"] = list(destination)
            if self._step_toward(world, animal, *destination, "patrol", tick):
                return
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        rotation = (animal.id.int + tick) % len(directions)
        ordered = directions[rotation:] + directions[:rotation]
        candidates = [
            (animal.x + dx, animal.y + dy)
            for dx, dy in ordered
            if self._can_enter(world, animal.x + dx, animal.y + dy)
        ]
        preferred = [
            position
            for position in candidates
            if self._terrain_at(world, position) in profile["habitats"]
        ]
        choices = preferred or candidates
        if not choices:
            self._set_state(animal, "alert", tick)
            return
        animal.x, animal.y = choices[0]
        self._set_state(animal, "patrol", tick)

    def _step_toward(
        self,
        world: World,
        animal: Entity,
        target_x: int,
        target_y: int,
        state: str,
        tick: int,
        allow_diagonal: bool = False,
    ) -> bool:
        dx = 0 if target_x == animal.x else (1 if target_x > animal.x else -1)
        animal.metadata["movement_target"] = [target_x, target_y]
        dy = 0 if target_y == animal.y else (1 if target_y > animal.y else -1)
        candidates: list[tuple[int, int]] = []
        if allow_diagonal and dx != 0 and dy != 0:
            candidates.append((animal.x + dx, animal.y + dy))
        axis_steps = [(animal.x + dx, animal.y), (animal.x, animal.y + dy)]
        if abs(target_y - animal.y) > abs(target_x - animal.x):
            axis_steps.reverse()
        candidates.extend(axis_steps)
        for x, y in candidates:
            if (x, y) != (animal.x, animal.y) and self._can_enter(world, x, y):
                animal.x = x
                animal.y = y
                self._set_state(animal, state, tick)
                return True
        # A bounded local search lets wildlife go around shores and obstacles.
        start = (animal.x, animal.y)
        frontier = deque([(start, start)])
        visited = {start}
        original_distance = animal.distance_squared_to(target_x, target_y)
        while frontier and len(visited) < 128:
            position, first_step = frontier.popleft()
            for ox, oy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                neighbour = (position[0] + ox, position[1] + oy)
                if neighbour in visited or not self._can_enter(world, *neighbour):
                    continue
                visited.add(neighbour)
                step = neighbour if position == start else first_step
                if (neighbour[0] - target_x) ** 2 + (
                    neighbour[1] - target_y
                ) ** 2 < original_distance:
                    animal.x, animal.y = step
                    self._set_state(animal, state, tick)
                    return True
                frontier.append((neighbour, step))
        self._set_state(animal, "alert", tick)
        return False

    @staticmethod
    def _nearby_resources(
        world: World,
        animal: Entity,
        accepted: set[ResourceType],
        radius: int,
    ) -> list[ResourceNode]:
        resources = [
            resource
            for resource in world.resources.values()
            if not resource.depleted
            and resource.resource_type in accepted
            and animal.distance_squared_to(resource.x, resource.y) <= radius**2
        ]
        return sorted(
            resources,
            key=lambda item: (
                animal.distance_squared_to(item.x, item.y),
                str(item.id),
            ),
        )

    @staticmethod
    def _nearest_terrain(
        world: World,
        animal: Entity,
        terrains: set[TerrainType],
        radius: int,
    ) -> Any | None:
        candidates = [
            tile
            for x in range(animal.x - radius, animal.x + radius + 1)
            for y in range(animal.y - radius, animal.y + radius + 1)
            if (tile := world.retrieve_tile(x, y)) is not None
            and tile.terrain in terrains
        ]
        return min(
            candidates,
            key=lambda tile: animal.distance_squared_to(tile.x, tile.y),
            default=None,
        )

    @staticmethod
    def _terrain_near(
        world: World,
        x: int,
        y: int,
        terrains: set[TerrainType],
        radius: int,
    ) -> bool:
        return any(
            (tile := world.retrieve_tile(tx, ty)) is not None
            and tile.terrain in terrains
            for tx in range(x - radius, x + radius + 1)
            for ty in range(y - radius, y + radius + 1)
        )

    def _local_capacity(
        self,
        world: World,
        animal: Entity,
        species: str,
        history: SpeciesLifeHistory,
    ) -> int:
        """Scales capacity with suitable habitat and renewable food availability."""
        habitats: set[TerrainType] = self.PROFILES[species]["habitats"]
        radius = history.territory_radius
        habitat_tiles = sum(
            1
            for x in range(animal.x - radius, animal.x + radius + 1)
            for y in range(animal.y - radius, animal.y + radius + 1)
            if (tile := world.retrieve_tile(x, y)) is not None
            and tile.walkable
            and tile.terrain in habitats
        )
        area = max(1, (radius * 2 + 1) ** 2)
        habitat_ratio = habitat_tiles / area
        food_types: set[ResourceType] = self.PROFILES[species]["diet"]
        food_nodes = sum(
            1
            for resource in world.resources.values()
            if not resource.depleted
            and resource.resource_type in food_types
            and animal.distance_squared_to(resource.x, resource.y) <= radius**2
        )
        prey_bonus = 0
        if species in {"wolf", "fox"}:
            prey_bonus = sum(
                1
                for other in world.entities.values()
                if other.active
                and other.kind == EntityKind.ANIMAL
                and str(other.metadata.get("species", ""))
                in ({"rabbit", "deer"} if species == "wolf" else {"rabbit", "duck"})
                and animal.distance_squared_to(other.x, other.y) <= radius**2
            )
        support = habitat_ratio * 0.75 + min(0.25, (food_nodes + prey_bonus) * 0.035)
        return max(2, round(history.local_capacity * support))

    @staticmethod
    def _local_population(
        world: World, animal: Entity, species: str, radius: int
    ) -> int:
        return sum(
            1
            for other in world.entities.values()
            if other.active
            and other.kind == EntityKind.ANIMAL
            and str(other.metadata.get("species", "")) == species
            and animal.distance_squared_to(other.x, other.y) <= radius**2
        )

    @staticmethod
    def _birth_position(
        world: World, mother: Entity, offset: int
    ) -> tuple[int, int] | None:
        positions = [
            (mother.x, mother.y),
            (mother.x + 1, mother.y),
            (mother.x - 1, mother.y),
            (mother.x, mother.y + 1),
            (mother.x, mother.y - 1),
        ]
        for index in range(len(positions)):
            x, y = positions[(index + offset) % len(positions)]
            if AnimalService._can_enter(world, x, y):
                return x, y
        return None

    @staticmethod
    def _terrain_at(world: World, position: tuple[int, int]) -> TerrainType | None:
        tile = world.retrieve_tile(*position)
        return tile.terrain if tile is not None else None

    @staticmethod
    def _set_state(
        animal: Entity, state: str, tick: int, target_id: str | None = None
    ) -> None:
        animal.metadata["state"] = state
        animal.metadata["behavior_reason"] = {
            "sleep": "Resting during this species' inactive hours.",
            "rest": "Recovering energy before continuing.",
            "graze": "Eating nearby vegetation to satisfy hunger.",
            "feed": "Eating a reachable food source.",
            "drink": "Drinking at a nearby water source.",
            "seek_water": "Thirst is rising; travelling to water.",
            "hunt": "Tracking nearby prey to satisfy hunger.",
            "flee": "Moving away from a nearby threat.",
            "return_home": "Returning to suitable habitat to rest.",
            "patrol": "Exploring the home territory for food and water.",
            "forage": "Travelling to a known food source.",
            "regroup": "Rejoining nearby members of the same species.",
            "alert": "The route is obstructed; watching for a safe opening.",
            "seek_weather_shelter": "Seeking cover from severe weather.",
            "shelter_weather": "Waiting under cover until the weather improves.",
        }.get(state, state.replace("_", " ").capitalize())
        if state in {"sleep", "rest", "graze", "feed", "drink"}:
            animal.metadata.pop("movement_target", None)
        animal.metadata["last_state_tick"] = tick
        if state in {
            "flee",
            "forage",
            "hunt",
            "patrol",
            "regroup",
            "return_home",
            "seek_water",
            "seek_weather_shelter",
        }:
            animal.metadata["last_move_tick"] = tick
        if target_id is not None:
            animal.metadata["last_target"] = target_id

    @staticmethod
    def _can_enter(world: World, x: int, y: int) -> bool:
        tile = world.retrieve_tile(x, y)
        if tile is None or not tile.walkable:
            return False
        if any(
            structure.x == x
            and structure.y == y
            and structure.structure_type != StructureType.ROAD
            for structure in world.structures.values()
        ):
            return False
        return not any(
            resource.x == x
            and resource.y == y
            and not resource.depleted
            and resource.resource_type
            in {ResourceType.TREE, ResourceType.STONE, ResourceType.ORE}
            for resource in world.resources.values()
        )
