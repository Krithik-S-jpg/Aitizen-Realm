"""Species-specific deterministic wildlife behavior."""

from collections import deque
from typing import Any

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.calendar import DayPhase, Season, calendar_at_tick
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.resource import ResourceNode, ResourceType
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

    def advance_all(self, tick: int) -> None:
        """Advances each animal from its species and survival pressure."""
        world = self._repository.get()
        if world is None:
            return
        calendar = calendar_at_tick(tick)
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
            cadence = min(2, max(1, int(animal.metadata.get("move_cadence", 1))))
            if tick % cadence != animal.id.int % cadence:
                continue
            self._decide(world, animal, calendar.phase, calendar.season, tick)

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
            if animal.distance_squared_to(home_x, home_y) > 4 and self._step_toward(
                world, animal, home_x, home_y, "return_home", tick
            ):
                return
            if needs is not None:
                needs.rest(3.0)
            self._set_state(animal, "sleep", tick)
            return
        if species in {"wolf", "fox"}:
            if (needs is None or needs.hunger > 18.0) and self._hunt(
                world, animal, tick
            ):
                return
        elif needs is not None and needs.hunger > 18.0:
            if self._forage(world, animal, profile, tick):
                return
            if species == "boar" and self._root_for_food(world, animal, tick):
                return
        if bool(profile["social"]) and self._regroup(world, animal, species, tick):
            return
        self._patrol_habitat(world, animal, profile, tick)

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
            self._consume_prey(hunter, target, tick)
            return True
        moved = self._step_toward(
            world, hunter, target.x, target.y, "hunt", tick, allow_diagonal=True
        )
        if moved and hunter.distance_squared_to(target.x, target.y) <= 2:
            self._consume_prey(hunter, target, tick)
        return moved

    def _consume_prey(self, hunter: Entity, target: Entity, tick: int) -> None:
        """Completes a close-range predator-prey interaction."""
        target.active = False
        target.metadata["death_tick"] = tick
        target.metadata["killed_by"] = str(hunter.id)
        self._set_state(target, "dead", tick)
        self._set_state(hunter, "feed", tick, str(target.id))
        hunter.metadata["meals"] = int(hunter.metadata.get("meals", 0)) + 1
        if hunter.needs is not None:
            hunter.needs.eat(38.0)
            hunter.needs.energy = min(100.0, hunter.needs.energy + 7.0)

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
    def _terrain_at(world: World, position: tuple[int, int]) -> TerrainType | None:
        tile = world.retrieve_tile(*position)
        return tile.terrain if tile is not None else None

    @staticmethod
    def _set_state(
        animal: Entity, state: str, tick: int, target_id: str | None = None
    ) -> None:
        animal.metadata["state"] = state
        animal.metadata["last_state_tick"] = tick
        if state in {
            "flee",
            "forage",
            "hunt",
            "patrol",
            "regroup",
            "return_home",
            "seek_water",
        }:
            animal.metadata["last_move_tick"] = tick
        if target_id is not None:
            animal.metadata["last_target"] = target_id

    @staticmethod
    def _can_enter(world: World, x: int, y: int) -> bool:
        tile = world.retrieve_tile(x, y)
        return tile is not None and tile.walkable
