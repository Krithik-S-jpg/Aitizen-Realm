"""Episodic memory and selective knowledge-transfer tests."""

import pytest

from app.application.services.communication_service import CommunicationService
from app.application.services.entity_service import EntityService
from app.application.services.memory_service import MemoryService
from app.application.services.perception_service import PerceptionService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import EntityKind
from app.domain.models.memory import EpisodeType, MessageType
from app.domain.models.resource import ResourceNode, ResourceType
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _systems() -> tuple[
    EntityService, PerceptionService, MemoryService, CommunicationService
]:
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(16, 16)
    world.add_resource(
        ResourceNode(
            resource_type=ResourceType.TREE,
            x=5,
            y=6,
            quantity=20.0,
            capacity=20.0,
        )
    )
    repository.save(world)
    memory = MemoryService(repository)
    return (
        EntityService(repository),
        PerceptionService(repository),
        memory,
        CommunicationService(repository, memory),
    )


def test_direct_observation_builds_confident_spatial_memory() -> None:
    """Repeated firsthand observations refresh confidence and counts."""
    entities, perception, memory, _ = _systems()
    observer = entities.create(EntityKind.AGENT, "Observer", 5, 5, 2)
    perception.observe(observer.id, 3)
    knowledge = perception.knowledge(observer.id)
    resource = next(iter(knowledge.resources.values()))
    assert resource.first_seen_tick == 3
    assert resource.observation_count == 1
    assert resource.confidence == 1.0

    perception.observe(observer.id, 8)
    assert resource.last_seen_tick == 8
    assert resource.observation_count == 2
    memory.decay_all(58)
    assert resource.confidence == 0.9


def test_discoveries_and_action_events_are_recallable_episodes() -> None:
    """Personal experiences can be recalled by type and location."""
    entities, perception, memory, _ = _systems()
    observer = entities.create(EntityKind.AGENT, "Observer", 5, 5, 2)
    perception.observe(observer.id, 4)
    memory.remember(
        observer.id,
        EpisodeType.DANGER,
        7,
        "A severe storm approached.",
        importance=0.9,
    )

    discoveries = memory.recall(observer.id, episode_type=EpisodeType.DISCOVERY)
    assert len(discoveries) == 1
    assert discoveries[0].details["discovery_count"] == 1
    nearby = memory.recall(observer.id, near_x=5, near_y=5, radius=1)
    assert [episode.tick for episode in nearby] == [7, 4]


def test_communication_transfers_only_selected_knowledge_with_provenance() -> None:
    """Secondhand facts are bounded, attributed, and less confident."""
    entities, perception, _, communication = _systems()
    sender = entities.create(EntityKind.AGENT, "Sender", 5, 5, 2)
    recipient = entities.create(EntityKind.AGENT, "Recipient", 6, 5, 2)
    perception.observe(sender.id, 2)
    sender_knowledge = perception.knowledge(sender.id)
    resource_id = next(iter(sender_knowledge.resources))

    message = communication.send(
        sender.id,
        recipient.id,
        "I found wood nearby.",
        3,
        {"resources": [resource_id]},
    )
    recipient_knowledge = perception.knowledge(recipient.id)
    shared = recipient_knowledge.resources[resource_id]
    assert message.message_type == MessageType.KNOWLEDGE
    assert message.transferred_count == 1
    assert shared.source_entity_id == sender.id
    assert shared.learned_at_tick == 3
    assert shared.confidence == 0.75
    assert recipient_knowledge.tiles == {}

    perception.observe(recipient.id, 4)
    assert shared.source_entity_id is None
    assert shared.confidence == 1.0


def test_communication_creates_memories_for_both_participants() -> None:
    """Sender and recipient retain their own perspective of a conversation."""
    entities, _, memory, communication = _systems()
    sender = entities.create(EntityKind.AGENT, "Sender", 5, 5)
    recipient = entities.create(EntityKind.AGENT, "Recipient", 6, 5)
    communication.send(sender.id, recipient.id, "Stay near the shelter.", 5)

    sender_memory = memory.recall(sender.id, episode_type=EpisodeType.COMMUNICATION)
    recipient_memory = memory.recall(
        recipient.id, episode_type=EpisodeType.COMMUNICATION
    )
    assert "Told Recipient" in sender_memory[0].summary
    assert "Heard from Sender" in recipient_memory[0].summary
    assert communication.history(sender.id) == communication.history(recipient.id)


def test_entities_outside_range_cannot_communicate() -> None:
    """Communication cannot transfer knowledge across arbitrary distance."""
    entities, _, _, communication = _systems()
    sender = entities.create(EntityKind.AGENT, "Sender", 1, 1)
    recipient = entities.create(EntityKind.AGENT, "Recipient", 15, 15)
    with pytest.raises(ValueError, match="outside"):
        communication.send(sender.id, recipient.id, "Can you hear me?", 1)
