"""Persistent water habitats, limited harvests and tick-driven marine wildlife."""

from math import cos, sin
from uuid import NAMESPACE_URL, uuid5

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.inventory import Inventory
from app.domain.models.world import Tile, World


class MarineService:
    """Own habitat initialization, marine decisions and finite dive harvests."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Use the same authoritative store as navigation and checkpoints."""
        self.repository = repository

    @staticmethod
    def wet(tile: Tile | None) -> bool:
        """Identify water tiles without relying on surface walkability."""
        return tile is not None and tile.terrain.value in {"WATER", "OCEAN"}

    @staticmethod
    def sample(x: int, y: int, seed: int = 0) -> float:
        """Return stable spatial noise without mutating a global RNG."""
        value = (x * 374761393 + y * 668265263 + seed * 144269) & 0x7FFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0x7FFFFFFF
        return (value ^ (value >> 16)) / 2147483647

    def initialize(self, world: World) -> None:
        """Upgrade an uninitialized world once, preserving existing harvests."""
        if world.marine_initialized:
            return
        # Both a world version and tile presence guard against resetting harvests.
        count = sum(bool(e.metadata.get("marine")) for e in world.entities.values())
        for chunk in world.chunks.values():
            for tile in chunk.tiles.values():
                if not self.wet(tile) or "marine" in tile.metadata:
                    continue
                near_shore = any(
                    not self.wet(world.retrieve_tile(tile.x + dx, tile.y + dy))
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
                )
                patch = sin(tile.x * 0.19 + (world.seed or 0)) * cos(tile.y * 0.17)
                roll = self.sample(tile.x, tile.y, world.seed or 0)
                depth = 2 if near_shore else 12 if tile.terrain.value == "OCEAN" else 5
                habitat = (
                    "sand"
                    if near_shore
                    else "kelp"
                    if patch > 0.2
                    else "reef"
                    if patch < -0.25
                    else "rock"
                )
                landmark = "wreck" if roll > 0.995 else "cave" if roll > 0.985 else ""
                item = (
                    "salvage"
                    if landmark == "wreck"
                    else "mineral"
                    if habitat == "rock"
                    else "seaweed"
                    if habitat == "kelp"
                    else "pearl"
                    if roll > 0.9
                    else "shell"
                )
                tile.metadata["marine"] = dict(
                    depth=depth,
                    habitat=habitat,
                    landmark=landmark,
                    item=item,
                    remaining=3 if item != "pearl" else 1,
                )
                if roll > 0.045 or count >= 160:
                    continue
                species_roll = self.sample(tile.x, tile.y, (world.seed or 0) + 37)
                species = (
                    "crab"
                    if near_shore
                    else "shark"
                    if depth == 12 and species_roll < 0.04
                    else "jellyfish"
                    if species_roll < 0.24
                    else "reef_fish"
                )
                identity = uuid5(
                    NAMESPACE_URL, f"marine:{world.seed}:{tile.x}:{tile.y}"
                )
                world.entities[str(identity)] = Entity(
                    id=identity,
                    kind=EntityKind.ANIMAL,
                    name=species.replace("_", " ").title(),
                    x=tile.x,
                    y=tile.y,
                    metadata=dict(
                        marine=True,
                        underwater=True,
                        species=species,
                        state="swim",
                        hunger=20.0,
                        marine_tick=-1,
                        school=f"{tile.x // 8}:{tile.y // 8}",
                    ),
                )
                count += 1
        world.marine_initialized = True

    def advance_all(self, tick: int) -> None:
        """Advance active marine animals at most once per simulation tick."""
        world = self.repository.get()
        if world is None:
            return
        self.initialize(world)
        animals = [
            e for e in world.entities.values() if e.active and e.metadata.get("marine")
        ]
        # Bounded population and local neighbor tests; no rendering-frame AI work.
        for entity in animals:
            if not entity.active:
                continue
            data = entity.metadata
            if data.get("marine_tick", -1) >= tick:
                continue
            data["marine_tick"] = tick
            species = data["species"]
            data["hunger"] = min(100.0, data.get("hunger", 20.0) + 0.6)
            neighbors = [
                e
                for e in animals
                if e.active
                and e.id != entity.id
                and entity.distance_squared_to(e.x, e.y) <= 36
            ]
            threats = (
                [e for e in neighbors if e.metadata["species"] == "shark"]
                if species != "shark"
                else []
            )
            threats += [
                e
                for e in world.entities.values()
                if e.active
                and e.kind == EntityKind.AGENT
                and e.metadata.get("underwater")
                and entity.distance_squared_to(e.x, e.y) <= 9
            ]
            prey = [e for e in neighbors if e.metadata["species"] == "reef_fish"]
            target = None
            food_position = None
            state = (
                "drift"
                if species == "jellyfish"
                else "school"
                if species == "reef_fish"
                else "wander"
            )
            if threats:
                target = min(
                    threats, key=lambda e: entity.distance_squared_to(e.x, e.y)
                )
                state = "flee"
            elif species == "shark" and prey and data["hunger"] > 35:
                target = min(prey, key=lambda e: entity.distance_squared_to(e.x, e.y))
                state = "hunt"
                if entity.distance_squared_to(target.x, target.y) <= 1:
                    target.active = False
                    target.metadata["state"] = "dead"
                    data["hunger"] = max(0, data["hunger"] - 45)
                    data["state"] = "feed"
                    continue
            elif data["hunger"] > 30 and species != "shark":
                tile = world.retrieve_tile(entity.x, entity.y)
                food = tile.metadata.get("marine", {})
                if food.get("remaining", 0) > 0 and food.get("item") in {
                    "seaweed",
                    "shell",
                }:
                    food["remaining"] -= min(0.1, food["remaining"])
                    data["hunger"] = max(0, data["hunger"] - 12)
                    data["state"] = "feed"
                    continue
                food_tiles = [
                    candidate
                    for x in range(entity.x - 3, entity.x + 4)
                    for y in range(entity.y - 3, entity.y + 4)
                    if self.wet(candidate := world.retrieve_tile(x, y))
                    and candidate.metadata.get("marine", {}).get("remaining", 0) > 0
                    and candidate.metadata.get("marine", {}).get("item")
                    in {"seaweed", "shell"}
                ]
                if food_tiles:
                    source = min(
                        food_tiles, key=lambda t: entity.distance_squared_to(t.x, t.y)
                    )
                    food_position = (source.x, source.y)
                    state = "seek_food"
            if target is None and food_position is None and species == "reef_fish":
                peers = [
                    e
                    for e in neighbors
                    if e.metadata["species"] == species
                    and e.metadata["school"] == data["school"]
                ]
                if peers:
                    target = min(peers, key=lambda e: str(e.id))
            candidates = [
                (entity.x + dx, entity.y + dy)
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
            ]
            candidates = [
                p
                for p in candidates
                if self.wet(world.retrieve_tile(*p))
                and (
                    species != "crab"
                    or world.retrieve_tile(*p)
                    .metadata.get("marine", {})
                    .get("depth", 99)
                    <= 5
                )
            ]
            if candidates and (species != "crab" or tick % 2 == 0):

                def score(
                    p,
                    target=target,
                    state=state,
                    food_position=food_position,
                    species=species,
                    entity=entity,
                ):
                    jitter = self.sample(*p, tick + (world.seed or 0))
                    if target:
                        distance = (p[0] - target.x) ** 2 + (p[1] - target.y) ** 2
                        return distance * (1 if state == "flee" else -1) + jitter
                    if food_position:
                        return (
                            -(
                                (p[0] - food_position[0]) ** 2
                                + (p[1] - food_position[1]) ** 2
                            )
                            + jitter
                        )
                    if species == "jellyfish":
                        return (
                            (p[0] - entity.x) * sin(tick * 0.07)
                            + (p[1] - entity.y) * cos(tick * 0.07)
                            + jitter * 0.2
                        )
                    return jitter

                entity.x, entity.y = max(candidates, key=score)
            data["state"] = state

    def discover_and_collect(self, world: World, entity: Entity, tick: int) -> None:
        """Remember visited habitat and harvest only what physically fits."""
        tile = world.retrieve_tile(entity.x, entity.y)
        if not self.wet(tile):
            return
        self.initialize(world)
        data = tile.metadata["marine"]
        discoveries = entity.metadata.setdefault("marine_discoveries", {})
        key = f"{entity.x},{entity.y}"
        if key not in discoveries and (data["landmark"] or data["item"] == "pearl"):
            from app.application.services.memory_service import MemoryService
            from app.domain.models.memory import EpisodeType

            MemoryService(self.repository).remember(
                entity.id,
                EpisodeType.DISCOVERY,
                tick,
                f"Discovered underwater {data['landmark'] or data['item']} "
                f"at ({entity.x}, {entity.y}).",
                importance=0.85,
                details={"habitat": data["habitat"], "item": data["item"]},
            )
        discoveries.setdefault(
            key,
            dict(
                x=entity.x,
                y=entity.y,
                tick=tick,
                habitat=data["habitat"],
                landmark=data["landmark"],
                item=data["item"],
            ),
        )
        if (
            entity.metadata.get("dive_returning")
            or entity.metadata.get("dive_collected", 0) >= 3
        ):
            return
        inventory = world.inventories.setdefault(str(entity.id), Inventory())
        available = min(1.0, data["remaining"])
        if available <= 0:
            return
        accepted = inventory.add(data["item"], available)
        data["remaining"] -= accepted
        entity.metadata["dive_collected"] = (
            entity.metadata.get("dive_collected", 0) + accepted
        )
        if accepted:
            entity.metadata["dive_phase"] = "gather"
