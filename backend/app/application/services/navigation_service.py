"""Knowledge-constrained A-star routing and tick-controlled movement."""

import heapq
from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.navigation import MovementPlan, MovementStatus
from app.domain.models.resource import ResourceType
from app.domain.models.structure import StructureType
from app.domain.models.world import World


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
        knowledge = world.entity_knowledge.get(str(entity_id))
        destination_key = f"{destination_x},{destination_y}"
        if knowledge is None or destination_key not in knowledge.tiles:
            raise ValueError("Destination is outside the entity's known world.")
        destination = world.retrieve_tile(destination_x, destination_y)
        if destination is None or not destination.walkable:
            raise ValueError("Destination is not walkable.")
        path = self._find_path(world, entity, destination_x, destination_y)
        if path is None:
            raise ValueError("No known walkable route reaches the destination.")
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
            if entity.needs is not None and entity.needs.energy <= 0.0:
                plan.status = MovementStatus.BLOCKED
                continue
            next_x, next_y = plan.path[plan.next_step_index]
            tile = world.retrieve_tile(next_x, next_y)
            if (
                tile is None
                or not tile.walkable
                or self._structure_blocks(world, next_x, next_y)
            ):
                plan.status = MovementStatus.BLOCKED
                continue
            entity.x = next_x
            entity.y = next_y
            if entity.kind == EntityKind.AGENT:
                tile.metadata["foot_traffic"] = min(
                    1000, int(tile.metadata.get("foot_traffic", 0)) + 1
                )
            plan.next_step_index += 1
            plan.last_advanced_tick = tick
            if plan.next_step_index >= len(plan.path):
                plan.status = MovementStatus.ARRIVED

    def get_plan(self, entity_id: UUID) -> MovementPlan:
        """Returns the current movement plan for an entity."""
        plan = self._require_world().movement_plans.get(str(entity_id))
        if plan is None:
            raise LookupError("Entity has no movement plan.")
        return plan

    def cancel(self, entity_id: UUID) -> MovementPlan:
        """Cancels an unfinished route."""
        plan = self.get_plan(entity_id)
        if plan.status == MovementStatus.MOVING:
            plan.status = MovementStatus.CANCELLED
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
            and site.structure_type not in {StructureType.CAMPFIRE, StructureType.ROAD}
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
            not in {StructureType.CAMPFIRE, StructureType.ROAD}
            for structure in world.structures.values()
        )

    @staticmethod
    def _mobile_entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        if not entity.active or entity.kind == EntityKind.OBJECT:
            raise ValueError("Entity cannot move.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
