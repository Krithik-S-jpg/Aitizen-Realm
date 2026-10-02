"""Lifecycle operations for generic simulation entities."""

from uuid import UUID

from app.application.services.entity_presentation import activity_details
from app.application.services.danger_memory import memory_graph

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import CitizenAvatar, Entity, EntityKind, EntityKnowledge
from app.domain.models.inventory import Inventory
from app.domain.models.needs import NeedsState
from app.domain.models.world import World


class EntityService:
    """Creates and manages identities without adding autonomous behavior."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes the service against the authoritative world store."""
        self._repository = repository

    def create(
        self,
        kind: EntityKind,
        name: str,
        x: int,
        y: int,
        perception_radius: int = 6,
        tags: set[str] | None = None,
        avatar_id: CitizenAvatar = CitizenAvatar.SCOUT,
        auto_spawn: bool = False,
    ) -> Entity:
        """Creates an entity on a loaded, walkable world tile."""
        world = self._require_world()
        if auto_spawn:
            occupied = {(e.x, e.y) for e in world.entities.values() if e.active}
            occupied.update((s.x, s.y) for s in world.structures.values())
            candidates = (
                tile
                for chunk in world.chunks.values()
                for tile in chunk.iterate_tiles()
                if tile.walkable and (tile.x, tile.y) not in occupied
                and 0 <= tile.x < world.width and 0 <= tile.y < world.height
            )
            nearest = min(
                candidates,
                key=lambda tile: ((tile.x - x) ** 2 + (tile.y - y) ** 2, tile.y, tile.x),
                default=None,
            )
            if nearest is None:
                raise ValueError("No free walkable tile is available. Load or create a world with land.")
            x, y = nearest.x, nearest.y
        tile = world.retrieve_tile(x, y)
        if tile is None:
            raise LookupError("Entity tile is not loaded.")
        if not tile.walkable:
            raise ValueError("Entity requires a walkable tile.")
        entity = Entity(
            kind=kind,
            name=name,
            x=x,
            y=y,
            perception_radius=perception_radius,
            tags=tags or set(),
            avatar_id=avatar_id,
            needs=NeedsState()
            if kind in {EntityKind.AGENT, EntityKind.ANIMAL}
            else None,
        )
        world.entities[str(entity.id)] = entity
        world.entity_knowledge[str(entity.id)] = EntityKnowledge(observer_id=entity.id)
        world.episodes[str(entity.id)] = []
        world.inventories.setdefault(str(entity.id), Inventory())
        return entity

    def get(self, entity_id: UUID) -> Entity:
        """Returns an entity by stable identity."""
        entity = self._require_world().entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        return entity

    def list_active(self) -> list[Entity]:
        """Returns active entities in deterministic identity order."""
        entities = [
            item for item in self._require_world().entities.values() if item.active
        ]
        return sorted(entities, key=lambda item: str(item.id))

    def deactivate(self, entity_id: UUID) -> Entity:
        """Marks an entity inactive while retaining history and knowledge."""
        entity = self.get(entity_id)
        entity.active = False
        return entity

    def admin_overview(self) -> list[dict[str, object]]:
        """Returns operational details needed by the local simulation console."""
        world = self._require_world()
        result: list[dict[str, object]] = []
        for entity in self.list_active():
            key = str(entity.id)
            goal = world.goals.get(world.active_goals.get(key, ""))
            action = world.actions.get(world.active_actions.get(key, ""))
            knowledge = world.entity_knowledge.get(key)
            inventory = world.inventories.get(key)
            life_state = str(entity.metadata.get("state", "idle"))
            visible_action = (
                life_state
                if life_state in {"sleep", "seek_shelter"}
                or (
                    life_state == "socialize"
                    and action is not None
                    and "social_with" in action.target
                )
                else (
                    action.action_type.value.lower()
                    if action is not None
                    else life_state
                )
            )
            result.append(
                {
                    **entity.model_dump(mode="json"),
                    "kind": entity.kind.value.lower(),
                    "inventory": inventory.model_dump()
                    if inventory is not None
                    else None,
                    "goal": goal.goal_type.value.lower()
                    if goal is not None
                    else ("survive" if entity.kind == EntityKind.ANIMAL else "idle"),
                    "action": visible_action,
                    "decision_reason": goal.reason
                    if goal is not None
                    else entity.metadata.get(
                        "blocked_reason",
                        entity.metadata.get("last_decision_reason", ""),
                    ),
                    "decision_trace": entity.metadata.get("decision_trace", []),
                    "action_progress": action.progress_ratio
                    if action is not None
                    else 0.0,
                    "action_target": action.target if action is not None else {},
                    "knowledge": {
                        "tiles": len(knowledge.tiles),
                        "resources": len(knowledge.resources),
                        "structures": len(knowledge.structures),
                        "entities": len(knowledge.entities),
                    }
                    if knowledge is not None
                    else {},
                    **activity_details(world, entity),
                    "memory_graph": memory_graph(world, entity),
                }
            )
        return result

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
