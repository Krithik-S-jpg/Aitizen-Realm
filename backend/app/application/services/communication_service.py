"""Local messages and selective, provenance-aware knowledge transfer."""

from uuid import UUID

from app.application.services.memory_service import MemoryService
from app.application.services.society_service import SocietyService
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, KnowledgeRecord
from app.domain.models.memory import EpisodeType, Message, MessageType
from app.domain.models.world import World


class CommunicationService:
    """Allows nearby entities to talk without creating shared omniscience."""

    MAX_RANGE = 6
    MAX_SHARED_RECORDS = 25
    SHARE_CONFIDENCE = 0.75
    CATEGORIES = {"tiles", "resources", "structures", "entities"}

    def __init__(
        self,
        repository: IWorldRepository,
        memory_service: MemoryService,
        society_service: SocietyService | None = None,
    ) -> None:
        """Initializes communication and episodic recording."""
        self._repository = repository
        self._memory = memory_service
        self._society = society_service

    def send(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        content: str,
        tick: int,
        shared_records: dict[str, list[str]] | None = None,
    ) -> Message:
        """Delivers a local message and only the explicitly selected facts."""
        world = self._require_world()
        sender = self._entity(world, sender_id)
        recipient = self._entity(world, recipient_id)
        if sender.id == recipient.id:
            raise ValueError("An entity cannot message itself.")
        if sender.distance_squared_to(recipient.x, recipient.y) > self.MAX_RANGE**2:
            raise ValueError("Recipient is outside communication range.")
        requested = shared_records or {}
        if not set(requested) <= self.CATEGORIES:
            raise ValueError("Unknown knowledge category requested.")
        if sum(len(keys) for keys in requested.values()) > self.MAX_SHARED_RECORDS:
            raise ValueError("Message exceeds the knowledge sharing limit.")
        transferred = self._transfer(world, sender, recipient, requested, tick)
        message = Message(
            sender_id=sender.id,
            recipient_id=recipient.id,
            message_type=MessageType.KNOWLEDGE if requested else MessageType.SPEECH,
            tick=tick,
            content=content,
            shared_records=requested,
            transferred_count=transferred,
        )
        world.messages.append(message)
        if self._society is not None:
            self._society.register_interaction(sender.id, recipient.id, tick)
            self._society.register_interaction(recipient.id, sender.id, tick)
        participants = [sender.id, recipient.id]
        self._memory.remember(
            sender.id,
            EpisodeType.COMMUNICATION,
            tick,
            f"Told {recipient.name}: {content}",
            0.45,
            {"message_id": str(message.id), "transferred": transferred},
            participants,
        )
        self._memory.remember(
            recipient.id,
            EpisodeType.COMMUNICATION,
            tick,
            f"Heard from {sender.name}: {content}",
            0.45,
            {"message_id": str(message.id), "transferred": transferred},
            participants,
        )
        return message

    def history(self, entity_id: UUID) -> list[Message]:
        """Returns messages sent or received by one entity."""
        world = self._require_world()
        self._entity(world, entity_id)
        return [
            message
            for message in world.messages
            if entity_id in {message.sender_id, message.recipient_id}
        ]

    def _transfer(
        self,
        world: World,
        sender: Entity,
        recipient: Entity,
        requested: dict[str, list[str]],
        tick: int,
    ) -> int:
        sender_knowledge = world.entity_knowledge[str(sender.id)]
        recipient_knowledge = world.entity_knowledge[str(recipient.id)]
        transferred = 0
        for category, keys in requested.items():
            source: dict[str, KnowledgeRecord] = getattr(sender_knowledge, category)
            destination: dict[str, KnowledgeRecord] = getattr(
                recipient_knowledge, category
            )
            for key in keys:
                record = source.get(key)
                if record is None:
                    continue
                confidence = min(record.confidence, self.SHARE_CONFIDENCE)
                existing = destination.get(key)
                if existing is not None and existing.confidence >= confidence:
                    continue
                destination[key] = KnowledgeRecord(
                    key=record.key,
                    category=record.category,
                    x=record.x,
                    y=record.y,
                    first_seen_tick=record.first_seen_tick,
                    last_seen_tick=record.last_seen_tick,
                    learned_at_tick=tick,
                    observation_count=record.observation_count,
                    confidence=confidence,
                    source_entity_id=sender.id,
                    data=record.data.copy(),
                )
                transferred += 1
        return transferred

    @staticmethod
    def _entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        if not entity.active:
            raise ValueError("Inactive entities cannot communicate.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
