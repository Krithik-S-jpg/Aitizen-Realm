"""Knowledge-constrained A-star routing and tick-controlled movement."""

import heapq
from collections import deque
from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.navigation import MovementPlan, MovementStatus
from app.domain.models.resource import ResourceType
from app.domain.models.structure import StructureType
from app.domain.models.world import World
from app.application.services.marine_service import MarineService


class NavigationService:
    """Plans routes and applies at most one movement step per world tick."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes navigation against the authoritative world store."""
        self._repository = repository

    def plan(
        self, entity_id: UUID, destination_x: int, destination_y: int, tick: int
    ) -> MovementPlan:
        """Plans a least-cost path using only tiles this entity has observed."""
        world = self._require_world()
        entity = self._mobile_entity(world, entity_id)
        if entity.metadata.get("carried_by") or entity.metadata.get("infant_carried_by"):
            raise ValueError("A carried casualty cannot choose an independent route.")
        if entity.kind == EntityKind.AGENT:
            from app.application.services.family_service import stage
            life_stage = stage(entity)
            if life_stage == "infant":
                raise ValueError("Infants must be carried by a guardian.")
            if life_stage in {"toddler", "child"}:
                guardian = world.entities.get(str(entity.metadata.get("guardian_id", "")))
                if not guardian or not guardian.active or guardian.distance_squared_to(entity.x, entity.y) > 2 or guardian.distance_squared_to(destination_x, destination_y) > 2:
                    raise ValueError("Young children need a nearby guardian throughout local movement.")
        if entity.metadata.get("dive_trip"):
            raise ValueError("Finish the current dive before choosing another route.")
        if entity.metadata.get("in_cave"):
            raise ValueError("Return through the cave entrance before surface travel.")
        knowledge = world.entity_knowledge.get(str(entity_id))
        destination_key = f"{destination_x},{destination_y}"
        if knowledge is None or destination_key not in knowledge.tiles:
            raise ValueError("Destination is outside the entity's known world.")
        destination = world.retrieve_tile(destination_x, destination_y)
        if destination is None or not destination.walkable:
            raise ValueError("Destination is not walkable.")
        path = self._find_path(world, entity, destination_x, destination_y)
        if path is None and entity.kind == EntityKind.AGENT:
            path = self._water_path(world, entity, destination_x, destination_y)
        if path is None:
            raise ValueError("No known walkable route reaches the destination.")
        if entity.kind == EntityKind.AGENT and life_stage in {"toddler", "child"}:
            if any(not world.retrieve_tile(x,y).walkable or guardian.distance_squared_to(x,y) > 2 for x,y in path):
                raise ValueError("Child route leaves the supervised land area.")
        status = MovementStatus.ARRIVED if len(path) == 1 else MovementStatus.MOVING
        plan = MovementPlan(
            entity_id=entity.id,
            destination_x=destination_x,
            destination_y=destination_y,
            path=path,
            status=status,
            planned_at_tick=tick,
        )
        world.movement_plans[str(entity.id)] = plan
        return plan

    def advance_all(self, tick: int) -> None:
        """Applies one valid route step to every moving entity."""
        world = self._require_world()
        for key in sorted(world.movement_plans):
            plan = world.movement_plans[key]
            if plan.status != MovementStatus.MOVING:
                continue
            entity = world.entities.get(key)
            if entity is None or not entity.active:
                plan.status = MovementStatus.CANCELLED
                continue
            if entity.metadata.get("carried_by") or entity.metadata.get("infant_carried_by") or entity.metadata.get("rescue_controlled"):
                plan.status = MovementStatus.CANCELLED
                continue
            if plan.last_advanced_tick == tick:
                continue
            if entity.metadata.get("dive_trip") and not entity.metadata.get(
                "dive_returning"
            ):
                # Reserve the complete retrace cost plus a safety margin before
                # spending another tick on exploration.
                steps_home = max(0, plan.next_step_index - 1)
                oxygen = float(entity.metadata.get("oxygen", 100))
                energy = entity.needs.energy if entity.needs else 0
                reserve = 24 + min(12, float(entity.metadata.get("learned_dive_reserve", 0)))
                if (
                    oxygen <= (steps_home + 1) * 12 + reserve
                    or energy <= (steps_home + 1) * 6 + reserve
                ):
                    # An observed tight return budget increases future caution.
                    entity.metadata["learned_dive_reserve"] = min(12, reserve - 24 + 3)
                    entity.metadata["dive_lesson"] = {"tick": tick, "oxygen": oxygen, "energy": energy,
                                                     "reason": "Turned back to preserve the return budget"}
                    plan = self.return_from_dive(entity.id, tick)
                    if plan.status != MovementStatus.MOVING:
                        continue
            if entity.needs is not None and entity.needs.energy <= 0.0:
                plan.status = MovementStatus.BLOCKED
                entity.metadata.update(underwater=False, dive_trip=False)
                continue
            next_x, next_y = plan.path[plan.next_step_index]
            if entity.kind == EntityKind.AGENT:
                from app.application.services.family_service import stage
                if stage(entity) in {"toddler", "child"}:
                    guardian = world.entities.get(str(entity.metadata.get("guardian_id", "")))
                    if not guardian or not guardian.active or guardian.distance_squared_to(next_x, next_y) > 2:
                        plan.status = MovementStatus.CANCELLED
                        entity.metadata["care_status"] = "Waiting safely for guardian"
                        continue
            tile = world.retrieve_tile(next_x, next_y)
            if (
                tile is None
                or (
                    not tile.walkable and not self._can_enter_water(world, entity, tile)
                )
                or self._structure_blocks(world, next_x, next_y)
            ):
                plan.status = MovementStatus.BLOCKED
                entity.metadata.update(underwater=False, dive_trip=False)
                continue
            entity.x = next_x
            entity.y = next_y
            if entity.metadata.get("aboard") or entity.metadata.get("dive_trip"):
                from app.application.services.perception_service import (
                    PerceptionService,
                )

                PerceptionService(self._repository).observe(entity.id, tick)
            vessel = world.entities.get(str(entity.metadata.get("boat_id", "")))
            if (
                vessel
                and entity.metadata.get("aboard")
                and not entity.metadata.get("dive_trip")
            ):
                vessel.x, vessel.y = next_x, next_y
            if entity.metadata.get("dive_trip"):
                if plan.next_step_index >= len(plan.path) // 2:
                    entity.metadata["dive_returning"] = True
                water = tile.terrain.value in {"WATER", "OCEAN"}
                entity.metadata["underwater"] = water
                entity.metadata["oxygen"] = (
                    max(0, float(entity.metadata.get("oxygen", 100)) - 12)
                    if water
                    else 100
                )
                if water:
                    entity.metadata["dive_phase"] = (
                        "surface"
                        if plan.next_step_index == len(plan.path) - 2
                        else "return"
                        if entity.metadata.get("dive_returning")
                        else "descend"
                        if plan.next_step_index == 1
                        else "explore"
                    )
                    if plan.next_step_index > 1:
                        MarineService(self._repository).discover_and_collect(
                            world, entity, tick
                        )
                    explored = entity.metadata.setdefault("underwater_explored", [])
                    coordinate = [next_x, next_y]
                    if coordinate not in explored:
                        explored.append(coordinate)
                        del explored[:-128]
                if plan.next_step_index + 1 >= len(plan.path):
                    entity.metadata.update(
                        dive_trip=False,
                        underwater=False,
                        oxygen=100,
                        dive_phase="surfaced",
                    )
            if tile.terrain.value in {"WATER", "OCEAN"} and not tile.walkable:
                boat = self._has_boat(world, entity) and not entity.metadata.get(
                    "dive_trip"
                )
                entity.metadata["travel_mode"] = "boat" if boat else "swim"
                if entity.needs:
                    entity.needs.energy = max(
                        0, entity.needs.energy - (0.5 if boat else 6)
                    )
            else:
                entity.metadata["travel_mode"] = "walk"
            if entity.kind == EntityKind.AGENT:
                tile.metadata["last_traffic_tick"] = tick
                tile.metadata["foot_traffic"] = min(
                    1000, int(tile.metadata.get("foot_traffic", 0)) + 1
                )
            plan.next_step_index += 1
            plan.last_advanced_tick = tick
            if plan.next_step_index >= len(plan.path):
                plan.status = MovementStatus.ARRIVED
                if vessel and entity.metadata.get("aboard"):
                    vessel.metadata["anchored"] = True

    def get_plan(self, entity_id: UUID) -> MovementPlan:
        """Returns the current movement plan for an entity."""
        plan = self._require_world().movement_plans.get(str(entity_id))
        if plan is None:
            raise LookupError("Entity has no movement plan.")
        return plan

    @staticmethod
    def _has_boat(world, entity):
        inventory = world.inventories.get(str(entity.id))
        boat = world.entities.get(str(entity.metadata.get("boat_id", "")))
        return (
            boat is not None
            and boat.active
            and boat.metadata.get("occupant") == str(entity.id)
        ) or (inventory is not None and inventory.items.get("boat", 0) >= 1)

    @classmethod
    def _can_enter_water(cls, world, entity, tile):
        from app.application.services.family_service import adult
        if entity.kind == EntityKind.AGENT and not adult(entity):
            return False
        if entity.metadata.get("flood_evacuating") and tile.metadata.get("flooded"):
            return entity.kind == EntityKind.AGENT and entity.needs is not None and entity.needs.energy > 0
        if entity.kind != EntityKind.AGENT:
            return False
        if cls._has_boat(world, entity):
            return (
                tile.terrain.value in {"WATER", "OCEAN"}
                and entity.needs is not None
                and entity.needs.energy > 2
            )
        return (
            tile.terrain.value == "WATER"
            and entity.needs is not None
            and entity.needs.energy >= 12
        )

    def _water_path(self, world, entity, x, y):
        """Known shore-to-shore crossings only, with a total water-step budget."""
        destination = world.retrieve_tile(x, y)
        if destination is None or not destination.walkable:
            return None
        boat = self._has_boat(world, entity)
        energy = entity.needs.energy if entity.needs else 0
        budget = min(80 if boat else 8, max(0, int((energy - 30) / (2 if boat else 8))))
        if budget == 0:
            return None
        knowledge = world.entity_knowledge[str(entity.id)]
        start = (entity.x, entity.y, 0)
        queue = deque([start])
        parents = {start: None}
        best = {(entity.x, entity.y): 0}
        while queue:
            current = queue.popleft()
            if current[:2] == (x, y):
                path = []
                while current is not None:
                    path.append(current[:2])
                    current = parents[current]
                return list(reversed(path))
            for nx, ny in self._neighbors(current[:2]):
                tile = world.retrieve_tile(nx, ny)
                if f"{nx},{ny}" not in knowledge.tiles or tile is None:
                    continue
                water = tile.terrain.value in {"WATER", "OCEAN"}
                if (
                    not tile.walkable and not self._can_enter_water(world, entity, tile)
                ) or self._structure_blocks(world, nx, ny):
                    continue
                spent = current[2] + int(water)
                if spent > budget or best.get((nx, ny), budget + 1) <= spent:
                    continue
                state = (nx, ny, spent)
                best[(nx, ny)] = spent
                parents[state] = current
                queue.append(state)
        return None

    def cancel(self, entity_id: UUID) -> MovementPlan:
        """Cancels an unfinished route."""
        plan = self.get_plan(entity_id)
        entity = self._require_world().entities.get(str(entity_id))
        if entity and entity.metadata.get("dive_trip"):
            raise ValueError(
                "Finish the short dive and return to shore before cancelling."
            )
        if plan.status == MovementStatus.MOVING:
            plan.status = MovementStatus.CANCELLED
        return plan

    def explore_underwater(self, entity_id: UUID, tick: int) -> MovementPlan:
        """A bounded breath-hold excursion from a known shore with a reserved return route."""
        world = self._require_world()
        entity = self._mobile_entity(world, entity_id)
        from app.application.services.family_service import needs_light_duties
        if needs_light_duties(entity):
            raise ValueError("Diving is unavailable during pregnancy and recovery.")
        from app.application.services.family_service import adult
        if not adult(entity):
            raise ValueError("Only adults can dive.")
        tile = world.retrieve_tile(entity.x, entity.y)
        boat = world.entities.get(str(entity.metadata.get("boat_id", "")))
        aboard = (
            boat is not None
            and boat.metadata.get("anchored")
            and boat.metadata.get("occupant") == str(entity.id)
        )
        if (
            entity.kind != EntityKind.AGENT
            or not tile
            or (not tile.walkable and not aboard)
        ):
            raise ValueError("Start diving from shore, not open water.")
        if not entity.needs or entity.needs.energy < 70 or entity.needs.health < 60:
            raise ValueError("Diving requires at least 70 energy and 60 health.")
        if entity.metadata.get("dive_trip"):
            raise ValueError("This citizen is already on a dive.")
        known = world.entity_knowledge.get(str(entity.id))
        start = (entity.x, entity.y)
        path = [start]
        for _ in range(3):
            candidates = [
                point
                for point in self._neighbors(path[-1])
                if point not in path
                and known
                and f"{point[0]},{point[1]}" in known.tiles
                and (candidate := world.retrieve_tile(*point)) is not None
                and candidate.terrain.value
                in ({"WATER", "OCEAN"} if aboard else {"WATER"})
                and not self._structure_blocks(world, *point)
            ]
            if not candidates:
                break
            path.append(sorted(candidates)[0])
        if len(path) < 2:
            raise ValueError(
                "No known shallow water beside this citizen. Move to a river or lake shore first."
            )
        path += list(reversed(path[:-1]))
        plan = MovementPlan(
            entity_id=entity.id,
            destination_x=start[0],
            destination_y=start[1],
            path=path,
            planned_at_tick=tick,
        )
        world.movement_plans[str(entity.id)] = plan
        entity.metadata.update(
            dive_trip=True,
            underwater=False,
            oxygen=100,
            dive_returning=False,
            dive_origin=list(start),
            dive_collected=0,
            dive_phase="descend",
            state="move",
            last_decision_reason="Explore shallow water and return before running out of breath.",
        )
        return plan

    def boat_command(self, entity_id, command, tick, x=None, y=None):
        """A crafted boat becomes a persistent, single-occupant world vessel."""
        from app.domain.models.inventory import Inventory

        world = self._require_world()
        entity = self._mobile_entity(world, entity_id)
        if entity.kind != EntityKind.AGENT or entity.metadata.get("dive_trip"):
            raise ValueError("Finish the dive before operating a boat.")
        inventory = world.inventories.setdefault(str(entity.id), Inventory())
        boat = world.entities.get(str(entity.metadata.get("boat_id", "")))
        if command == "craft":
            from app.application.services.resource_service import ResourceService

            ResourceService(self._repository).craft(str(entity.id), "boat")
            return {"crafted": "boat"}
        if command == "launch":
            if boat is not None and boat.active:
                raise ValueError(
                    "This citizen already has a launched boat; board it again."
                )
            tile = world.retrieve_tile(entity.x, entity.y)
            if not tile or not tile.walkable:
                raise ValueError("Launch from a shore tile.")
            candidates = [
                p
                for p in self._neighbors((entity.x, entity.y))
                if MarineService.wet(world.retrieve_tile(*p))
                and not self._structure_blocks(world, *p)
            ]
            if not candidates or not inventory.has({"boat": 1}):
                raise ValueError(
                    "Craft a boat and stand beside water before launching."
                )
            inventory.consume({"boat": 1})
            bx, by = candidates[0]
            boat = Entity(
                kind=EntityKind.OBJECT,
                name="Expedition boat",
                x=bx,
                y=by,
                metadata=dict(
                    vessel=True, owner=str(entity.id), occupant="", anchored=True
                ),
            )
            world.entities[str(boat.id)] = boat
            world.inventories[str(boat.id)] = Inventory(capacity=100)
            entity.metadata["boat_id"] = str(boat.id)
        elif command == "board":
            if (
                boat is None
                or boat.metadata.get("occupant")
                or entity.distance_squared_to(boat.x, boat.y) > 1
            ):
                raise ValueError("Stand beside your empty launched boat.")
            self.cancel(entity.id) if str(entity.id) in world.movement_plans else None
            entity.x, entity.y = boat.x, boat.y
            boat.metadata["occupant"] = str(entity.id)
            entity.metadata["travel_mode"] = "boat"
            entity.metadata["aboard"] = True
        elif (
            command == "unload"
            and boat is not None
            and entity.distance_squared_to(boat.x, boat.y) <= 1
        ):
            cargo = world.inventories[str(boat.id)]
            for item, quantity in list(cargo.items.items()):
                accepted = inventory.add(item, quantity)
                if accepted:
                    cargo.consume({item: accepted})
        elif boat is None or boat.metadata.get("occupant") != str(entity.id):
            raise ValueError("Board your boat first.")
        elif command == "anchor":
            self.cancel(entity.id) if str(entity.id) in world.movement_plans else None
            boat.metadata["anchored"] = True
        elif command == "row":
            if x is None or y is None or not entity.needs or entity.needs.energy < 20:
                raise ValueError(
                    "Choose a known water destination and recover at least 20 stamina."
                )
            known = world.entity_knowledge.get(str(entity.id))
            start = (entity.x, entity.y)
            queue = deque([start])
            parents = {start: None}
            while queue:
                point = queue.popleft()
                if point == (x, y):
                    break
                for neighbor in self._neighbors(point):
                    if (
                        neighbor not in parents
                        and known
                        and f"{neighbor[0]},{neighbor[1]}" in known.tiles
                        and MarineService.wet(world.retrieve_tile(*neighbor))
                        and not self._structure_blocks(world, *neighbor)
                    ):
                        parents[neighbor] = point
                        queue.append(neighbor)
            if (x, y) not in parents:
                raise ValueError("No known water route reaches that destination.")
            path = self._reconstruct(parents, (x, y))
            if len(path) > (entity.needs.energy - 10) * 2:
                raise ValueError("Destination exceeds rowing stamina reserve.")
            previous = world.movement_plans.get(str(entity.id))
            world.movement_plans[str(entity.id)] = MovementPlan(
                entity_id=entity.id,
                destination_x=x,
                destination_y=y,
                path=path,
                planned_at_tick=tick,
                status=MovementStatus.MOVING
                if len(path) > 1
                else MovementStatus.ARRIVED,
                last_advanced_tick=previous.last_advanced_tick if previous else None,
            )
            boat.metadata["anchored"] = False
        elif command == "store":
            if not boat.metadata["anchored"]:
                raise ValueError("Anchor before stowing cargo.")
            cargo = world.inventories[str(boat.id)]
            for item, quantity in list(inventory.items.items()):
                if item in {"shell", "pearl", "seaweed", "mineral", "salvage"}:
                    accepted = cargo.add(item, quantity)
                    if accepted:
                        inventory.consume({item: accepted})
        elif command == "disembark":
            candidates = [
                p
                for p in self._neighbors((entity.x, entity.y))
                if (t := world.retrieve_tile(*p))
                and t.walkable
                and not self._structure_blocks(world, *p)
            ]
            if not boat.metadata["anchored"] or not candidates:
                raise ValueError("Anchor beside clear shore before disembarking.")
            entity.x, entity.y = candidates[0]
            boat.metadata["occupant"] = ""
            entity.metadata.update(aboard=False, travel_mode="walk")
        else:
            raise ValueError("Unknown boat command.")
        return boat.model_dump(mode="json")

    def return_from_dive(self, entity_id: UUID, tick: int) -> MovementPlan:
        """Retrace visited tiles without teleporting or revealing unknown terrain."""
        world = self._require_world()
        entity = self._mobile_entity(world, entity_id)
        if not entity.metadata.get("dive_trip"):
            raise ValueError("This citizen is not on a dive.")
        old = self.get_plan(entity_id)
        if entity.metadata.get("dive_returning"):
            return old
        path = list(reversed(old.path[: old.next_step_index]))
        origin = path[-1]
        plan = MovementPlan(
            entity_id=entity.id,
            destination_x=origin[0],
            destination_y=origin[1],
            path=path,
            planned_at_tick=tick,
            status=MovementStatus.MOVING if len(path) > 1 else MovementStatus.ARRIVED,
            last_advanced_tick=old.last_advanced_tick,
        )
        world.movement_plans[str(entity.id)] = plan
        entity.metadata.update(
            dive_returning=True,
            last_decision_reason="Return along the known dive route with oxygen and stamina in reserve.",
        )
        if len(path) == 1:
            entity.metadata.update(dive_trip=False, underwater=False, oxygen=100)
        return plan

    def _find_path(
        self, world: World, entity: Entity, destination_x: int, destination_y: int
    ) -> list[tuple[int, int]] | None:
        start = (entity.x, entity.y)
        goal = (destination_x, destination_y)
        knowledge = world.entity_knowledge[str(entity.id)]
        frontier: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far: dict[tuple[int, int], float] = {start: 0.0}
        blocked = {
            (resource.x, resource.y)
            for resource in world.resources.values()
            if not resource.depleted
            and (
                resource.resource_type in {ResourceType.STONE, ResourceType.ORE}
                or (
                    resource.resource_type == ResourceType.TREE
                    and resource.growth >= 0.35
                )
            )
        }
        blocked.update(
            (site.x, site.y)
            for site in world.structures.values()
            if site.completed
            and site.structure_type not in {StructureType.CAMPFIRE, StructureType.ROAD, StructureType.BRIDGE}
        )
        roads = {
            (site.x, site.y)
            for site in world.structures.values()
            if site.completed and site.structure_type == StructureType.ROAD
        }
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                return self._reconstruct(came_from, goal)
            for neighbor in self._neighbors(current):
                key = f"{neighbor[0]},{neighbor[1]}"
                tile = world.retrieve_tile(*neighbor)
                if (
                    key not in knowledge.tiles
                    or tile is None
                    or not tile.walkable
                    or neighbor in blocked
                ):
                    continue
                new_cost = cost_so_far[current] + (
                    0.75 if neighbor in roads else tile.movement_cost
                )
                warning = entity.metadata.get("wildlife_warning", {})
                from app.application.services.adaptive_learning import danger_cost
                new_cost += danger_cost(entity, neighbor[0], neighbor[1], entity.metadata.get("decision_tick", 0))
                if warning.get("expires", -1) >= entity.metadata.get(
                    "decision_tick", 0
                ):
                    distance = (neighbor[0] - int(warning["x"])) ** 2 + (
                        neighbor[1] - int(warning["y"])
                    ) ** 2
                    if distance < 36:
                        new_cost += (36 - distance) * 0.5
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = (
                        new_cost
                        + (abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1]))
                        * 0.75
                    )
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current
        return None

    @staticmethod
    def _neighbors(position: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        x, y = position
        return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))

    @staticmethod
    def _reconstruct(
        came_from: dict[tuple[int, int], tuple[int, int] | None],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        path = [goal]
        current = goal
        while came_from[current] is not None:
            current = came_from[current]  # type: ignore[assignment]
            path.append(current)
        path.reverse()
        return path

    @staticmethod
    def _structure_blocks(world: World, x: int, y: int) -> bool:
        return any(
            resource.x == x
            and resource.y == y
            and not resource.depleted
            and (
                resource.resource_type in {ResourceType.STONE, ResourceType.ORE}
                or (
                    resource.resource_type == ResourceType.TREE
                    and resource.growth >= 0.35
                )
            )
            for resource in world.resources.values()
        ) or any(
            structure.x == x
            and structure.y == y
            and structure.completed
            and structure.structure_type
            not in {StructureType.CAMPFIRE, StructureType.ROAD, StructureType.BRIDGE}
            for structure in world.structures.values()
        )

    @staticmethod
    def _mobile_entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        if not entity.active or entity.kind == EntityKind.OBJECT:
            raise ValueError("Entity cannot move.")
        if entity.metadata.get("in_cave"):
            raise ValueError("Finish the cave trip before surface or water commands.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
