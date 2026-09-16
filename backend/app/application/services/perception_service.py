"""Radius-limited observation and persistent private world knowledge."""

from typing import Any
from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKnowledge, KnowledgeRecord
from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.world import World


class PerceptionService:
    """Prevents entities from accessing omniscient global world state."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes perception against the authoritative world store."""
        self._repository = repository

    def observe(self, entity_id: UUID, tick: int) -> dict[str, Any]:
        """Observes only objects inside the entity's circular sensing radius."""
        world = self._require_world()
        observer = self._entity(world, entity_id)
        if not observer.active:
            raise ValueError("Inactive entities cannot perceive the world.")
        knowledge = world.entity_knowledge.setdefault(
            str(entity_id), EntityKnowledge(observer_id=entity_id)
        )
        radius = observer.perception_radius
        known_resource_ids = set(knowledge.resources)
        known_structure_ids = set(knowledge.structures)
        known_entity_ids = set(knowledge.entities)
        visible_tiles: list[dict[str, Any]] = []
        for x in range(observer.x - radius, observer.x + radius + 1):
            for y in range(observer.y - radius, observer.y + radius + 1):
                if observer.distance_squared_to(x, y) > radius**2:
                    continue
                tile = world.retrieve_tile(x, y)
                if tile is None:
                    continue
                payload = {
                    "x": x,
                    "y": y,
                    "terrain": tile.terrain.value.lower(),
                    "walkable": tile.walkable,
                }
                visible_tiles.append(payload)
                key = f"{x},{y}"
                self._store_record(knowledge.tiles, key, "tile", x, y, tick, payload)

        visible_resources = [
            self._remember_resource(knowledge, resource, tick)
            for resource in world.resources.values()
            if not resource.depleted
            and observer.distance_squared_to(resource.x, resource.y) <= radius**2
        ]
        visible_structures = [
            self._remember_structure(knowledge, structure, tick)
            for structure in world.structures.values()
            if observer.distance_squared_to(structure.x, structure.y) <= radius**2
        ]
        visible_entities = [
            self._remember_entity(knowledge, entity, tick)
            for entity in world.entities.values()
            if entity.id != observer.id
            and entity.active
            and observer.distance_squared_to(entity.x, entity.y) <= radius**2
        ]
        knowledge.last_observation_tick = tick
        discoveries = (
            len(set(knowledge.resources) - known_resource_ids)
            + len(set(knowledge.structures) - known_structure_ids)
            + len(set(knowledge.entities) - known_entity_ids)
        )
        if discoveries > 0:
            world.episodes.setdefault(str(observer.id), []).append(
                Episode(
                    entity_id=observer.id,
                    episode_type=EpisodeType.DISCOVERY,
                    tick=tick,
                    x=observer.x,
                    y=observer.y,
                    summary=f"Discovered {discoveries} nearby world objects.",
                    importance=min(0.8, 0.3 + discoveries * 0.04),
                    details={"discovery_count": discoveries},
                )
            )
        return {
            "observer": self._entity_payload(observer),
            "tick": tick,
            "radius": radius,
            "tiles": visible_tiles,
            "resources": visible_resources,
            "structures": visible_structures,
            "entities": visible_entities,
            "knowledge_totals": self._knowledge_totals(knowledge),
        }

    def knowledge(self, entity_id: UUID) -> EntityKnowledge:
        """Returns only the selected entity's accumulated knowledge."""
        world = self._require_world()
        self._entity(world, entity_id)
        return world.entity_knowledge.setdefault(
            str(entity_id), EntityKnowledge(observer_id=entity_id)
        )

    @staticmethod
    def _remember_resource(
        knowledge: EntityKnowledge, resource: Any, tick: int
    ) -> dict[str, Any]:
        payload = {
            "id": str(resource.id),
            "type": resource.resource_type.value.lower(),
            "x": resource.x,
            "y": resource.y,
            "quantity": resource.quantity,
        }
        PerceptionService._store_record(
            knowledge.resources,
            str(resource.id),
            "resource",
            resource.x,
            resource.y,
            tick,
            payload,
        )
        return payload

    @staticmethod
    def _remember_structure(
        knowledge: EntityKnowledge, structure: Any, tick: int
    ) -> dict[str, Any]:
        payload = {
            "id": str(structure.id),
            "type": structure.structure_type.value.lower(),
            "x": structure.x,
            "y": structure.y,
            "completed": structure.completed,
            "storage_full": structure.stockpile.carried
            >= structure.stockpile.capacity * 0.9,
        }
        PerceptionService._store_record(
            knowledge.structures,
            str(structure.id),
            "structure",
            structure.x,
            structure.y,
            tick,
            payload,
        )
        return payload

    @staticmethod
    def _remember_entity(
        knowledge: EntityKnowledge, entity: Entity, tick: int
    ) -> dict[str, Any]:
        payload = PerceptionService._entity_payload(entity)
        PerceptionService._store_record(
            knowledge.entities,
            str(entity.id),
            "entity",
            entity.x,
            entity.y,
            tick,
            payload,
        )
        return payload

    @staticmethod
    def _entity_payload(entity: Entity) -> dict[str, Any]:
        return {
            "id": str(entity.id),
            "kind": entity.kind.value.lower(),
            "name": entity.name,
            "x": entity.x,
            "y": entity.y,
            "tags": sorted(entity.tags),
            "metadata": entity.metadata,
        }

    @staticmethod
    def _knowledge_totals(knowledge: EntityKnowledge) -> dict[str, int]:
        return {
            "tiles": len(knowledge.tiles),
            "resources": len(knowledge.resources),
            "structures": len(knowledge.structures),
            "entities": len(knowledge.entities),
        }

    @staticmethod
    def _store_record(
        collection: dict[str, KnowledgeRecord],
        key: str,
        category: str,
        x: int,
        y: int,
        tick: int,
        data: dict[str, Any],
    ) -> None:
        existing = collection.get(key)
        if existing is not None:
            existing.x = x
            existing.y = y
            existing.refresh(tick, data)
            return
        collection[key] = KnowledgeRecord(
            key=key,
            category=category,
            x=x,
            y=y,
            first_seen_tick=tick,
            last_seen_tick=tick,
            learned_at_tick=tick,
            data=data,
        )

    @staticmethod
    def _entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
