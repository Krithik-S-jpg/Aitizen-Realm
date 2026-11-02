"""Local messages and selective, provenance-aware knowledge transfer."""

from uuid import UUID
import math

from app.application.services.memory_service import MemoryService
from app.application.services.society_service import SocietyService
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKind, KnowledgeRecord
from app.domain.models.memory import EpisodeType, Message, MessageType
from app.domain.models.world import World


class CommunicationService:
    """Allows nearby entities to talk without creating shared omniscience."""

    MAX_RANGE = 6
    MAX_SHARED_RECORDS = 25
    SHARE_CONFIDENCE = 0.75
    CATEGORIES = {"tiles", "resources", "structures", "entities", "discoveries"}

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
        origin: str = "simulation",
    ) -> Message:
        """Delivers a local message and only the explicitly selected facts."""
        world = self._require_world()
        sender = self._entity(world, sender_id)
        recipient = self._entity(world, recipient_id)
        if sender.id == recipient.id:
            raise ValueError("An entity cannot message itself.")
        if sender.distance_squared_to(recipient.x, recipient.y) > self.MAX_RANGE**2:
            raise ValueError("Recipient is outside communication range.")
        if not self._available(sender) or not self._available(recipient):
            raise ValueError("Citizens must be awake and on the surface to talk.")
        if not content.strip() or len(content) > 240:
            raise ValueError("Speech must contain 1 to 240 characters.")
        requested = shared_records or {}
        if not set(requested) <= self.CATEGORIES:
            raise ValueError("Unknown knowledge category requested.")
        if sum(len(keys) for keys in requested.values()) > self.MAX_SHARED_RECORDS:
            raise ValueError("Message exceeds the knowledge sharing limit.")
        transferred = self._transfer(world, sender, recipient, requested, tick)
        reports = recipient.metadata.setdefault("resource_reports", {})
        for resource_id in requested.get("resources", []):
            record = world.entity_knowledge[str(sender.id)].resources.get(resource_id)
            key = f"{sender.id}:{resource_id}"
            verified = recipient.metadata.get("verified_reports", {})
            if record and key not in reports and key not in verified:
                reports[key] = {"source_id": str(sender.id), "resource_id": resource_id, "x": record.x, "y": record.y, "tick": tick}
        while len(reports) > 24:
            del reports[next(iter(reports))]
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
        if origin == "local_llm":
            for key in requested.get("discoveries", []):
                site = world.ancient_sites.get(key)
                if site and key in world.entity_knowledge[str(sender.id)].discoveries:
                    comments = site.setdefault("interpretations", [])
                    comments.append({"speaker": sender.name, "tick": tick, "text": content,
                                     "status": "Citizen interpretation, not verified history"})
                    del comments[:-10]
        entry = {"id": str(message.id), "tick": tick, "sender": sender.name,
                 "recipient": recipient.name, "content": content,
                 "sender_id": str(sender.id), "recipient_id": str(recipient.id), "origin": origin}
        for actor in (sender, recipient):
            actor.metadata["conversation"] = (actor.metadata.get("conversation", []) + [entry])[-40:]
        sender.metadata["speech"] = {"id": str(message.id), "text": content, "tick": tick}
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

    @staticmethod
    def _available(entity):
        data = entity.metadata
        return entity.active and entity.kind == EntityKind.AGENT and data.get("state") != "sleep" and not any(
            data.get(key) for key in ("in_cave", "underwater", "dive_trip", "aboard"))

    def give(self, sender_id, recipient_id, item, amount, tick):
        """Adjacent handoff: inventory conservation, no partial or remote gifts."""
        world = self._require_world()
        sender, recipient = self._entity(world, sender_id), self._entity(world, recipient_id)
        if sender.id == recipient.id or not self._available(sender) or not self._available(recipient):
            raise ValueError("Select two awake surface citizens.")
        if sender.distance_squared_to(recipient.x, recipient.y) > 2:
            raise ValueError("Walk beside the recipient before handing over supplies.")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Choose a positive finite quantity.")
        source, destination = world.inventories[str(sender.id)], world.inventories[str(recipient.id)]
        from app.application.services.diet import accepts
        if not accepts(recipient, item):
            raise ValueError("The recipient does not accept this food.")
        if not source.has({item: amount}):
            raise ValueError("The sender does not carry enough of that resource.")
        if destination.capacity - destination.carried < amount:
            raise ValueError("The recipient cannot carry this quantity.")
        source.consume({item: amount})
        destination.add(item, amount)
        message = self.send(sender.id, recipient.id, f"Here, take {amount:g} {item.replace('_', ' ')}.", tick)
        sender.metadata["handoff"] = {"id": str(message.id), "item": item, "amount": amount, "recipient_id": str(recipient.id)}
        if self._society is not None:
            bond = self._society.register_interaction(recipient.id, sender.id, tick)
            bond.trust = min(1.0, bond.trust + 0.08)
        self._memory.remember(recipient.id, EpisodeType.COMMUNICATION, tick,
                              f"{sender.name} helped me with {amount:g} {item}.", 0.8,
                              {"message_id": str(message.id), "item": item, "amount": amount,
                               "consequence": "Trust gained from actual help"}, [sender.id])
        return {"item": item, "amount": amount, "message_id": str(message.id)}

    def advance_all(self, tick):
        world = self._require_world()
        from app.application.services.flood_response import warn_neighbors
        warn_neighbors(self, world, tick)
        from app.application.services.citizen_dialogue import dialogue
        from app.core.config import settings
        dialogue.advance(self, world, tick)
        citizens = [e for e in world.entities.values() if self._available(e) and "autonomous" in e.tags]
        from app.application.services.community_routines import complete_deliveries, converse
        complete_deliveries(self, world, tick)
        for sender in citizens:
            if tick < sender.metadata.get("next_conversation_tick", 0):
                continue
            nearby = [e for e in citizens if e.id != sender.id and sender.distance_squared_to(e.x, e.y) <= 4
                      and tick >= e.metadata.get("next_conversation_tick", 0)]
            if not nearby:
                continue
            recipient = min(nearby, key=lambda e: (
                -(world.social_bonds.get(f"{sender.id}:{e.id}").trust
                  if f"{sender.id}:{e.id}" in world.social_bonds else 0),
                sender.distance_squared_to(e.x, e.y), str(e.id)))
            sender.metadata["next_conversation_tick"] = recipient.metadata["next_conversation_tick"] = tick + 24
            if converse(self, world, sender, recipient, tick):
                continue
            source = world.inventories.get(str(sender.id))
            if source and recipient.needs and recipient.needs.hunger >= 45 and sender.needs and sender.needs.hunger < 40:
                for food in ("cooked_fish", "food", "fruit", "meat", "mushroom"):
                    from app.application.services.diet import accepts
                    if not accepts(recipient, food):
                        continue
                    if source.items.get(food, 0) >= 4 and sender.distance_squared_to(recipient.x, recipient.y) <= 2:
                        try:
                            self.give(sender.id, recipient.id, food, 2, tick)
                            self.send(recipient.id, sender.id, "Thank you. I was hungry; I can eat this now.", tick)
                            break
                        except ValueError:
                            continue
                else:
                    self.send(recipient.id, sender.id, "I am hungry. Do you have food to spare?", tick)
                continue
            from app.application.services.conversation_topics import discuss
            if settings.OLLAMA_MODEL:
                dialogue.request(world, sender, recipient, tick, settings.OLLAMA_MODEL)
            else:
                discuss(self, world, sender, recipient, tick)

    def barter(self, first_id, second_id, offered, requested, tick):
        """Exchange one unit of each material atomically between adjacent citizens."""
        world = self._require_world()
        first, second = self._entity(world, first_id), self._entity(world, second_id)
        if first.id == second.id or not all(self._available(e) for e in (first, second)):
            raise ValueError("Two awake citizens are required.")
        if first.distance_squared_to(second.x, second.y) > 2 or offered == requested:
            raise ValueError("Barter requires adjacent citizens and different goods.")
        a, b = world.inventories[str(first.id)], world.inventories[str(second.id)]
        from app.application.services.diet import accepts
        if not accepts(first, requested) or not accepts(second, offered):
            raise ValueError("Barter does not match the recipients' diets.")
        if not a.has({offered: 1}) or not b.has({requested: 1}):
            raise ValueError("Both sides must carry their offered goods.")
        # Equal unit quantities preserve each pack's weight and capacity.
        if a.carried > a.capacity or b.carried > b.capacity:
            raise ValueError("Unload overfull inventories before trading.")
        a.consume({offered: 1})
        b.consume({requested: 1})
        a.add(requested, 1)
        b.add(offered, 1)
        self.send(first.id, second.id, f"Traded one {offered} for your {requested}. Thank you.", tick)
        from app.application.services.village_service import record
        group = world.groups.get(str(first.group_id))
        if group:
            record(group, tick, f"{first.name} and {second.name} exchanged {offered} for {requested}.")

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
                if existing is not None and existing.confidence >= confidence and not (
                    category == "discoveries" and record.data.get("inspected") and not existing.data.get("inspected")
                ):
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
