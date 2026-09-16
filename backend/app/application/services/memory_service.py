"""Episodic recall and confidence decay for spatial knowledge."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.world import World


class MemoryService:
    """Stores personal episodes and manages confidence in remembered facts."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes memory against the authoritative world store."""
        self._repository = repository

    def remember(
        self,
        entity_id: UUID,
        episode_type: EpisodeType,
        tick: int,
        summary: str,
        importance: float = 0.5,
        details: dict[str, object] | None = None,
        participants: list[UUID] | None = None,
    ) -> Episode:
        """Stores one personal event at the entity's current location."""
        world = self._require_world()
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        episode = Episode(
            entity_id=entity_id,
            episode_type=episode_type,
            tick=tick,
            x=entity.x,
            y=entity.y,
            summary=summary,
            importance=importance,
            details=details or {},
            participants=participants or [],
        )
        world.episodes.setdefault(str(entity_id), []).append(episode)
        return episode

    def recall(
        self,
        entity_id: UUID,
        limit: int = 20,
        episode_type: EpisodeType | None = None,
        near_x: int | None = None,
        near_y: int | None = None,
        radius: int = 5,
    ) -> list[Episode]:
        """Recalls important recent episodes, optionally by type or location."""
        world = self._require_world()
        if str(entity_id) not in world.entities:
            raise LookupError("Entity does not exist.")
        episodes = world.episodes.get(str(entity_id), [])
        matches = [
            episode
            for episode in episodes
            if (episode_type is None or episode.episode_type == episode_type)
            and (
                near_x is None
                or near_y is None
                or (episode.x - near_x) ** 2 + (episode.y - near_y) ** 2 <= radius**2
            )
        ]
        return sorted(
            matches,
            key=lambda item: (item.tick, item.importance, str(item.id)),
            reverse=True,
        )[:limit]

    def decay_all(self, tick: int) -> None:
        """Reduces confidence in facts that have not been refreshed."""
        world = self._require_world()
        for knowledge in world.entity_knowledge.values():
            for collection in (
                knowledge.tiles,
                knowledge.resources,
                knowledge.structures,
                knowledge.entities,
            ):
                for record in collection.values():
                    age = max(0, tick - record.last_seen_tick)
                    ceiling = 0.75 if record.source_entity_id is not None else 1.0
                    record.confidence = max(0.1, ceiling - age * 0.002)

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
