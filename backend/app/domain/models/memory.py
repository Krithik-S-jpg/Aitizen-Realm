"""Episodic memories and local communication records."""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EpisodeType(StrEnum):
    """Kinds of personally experienced simulation events."""

    DISCOVERY = "DISCOVERY"
    ACTION_RESULT = "ACTION_RESULT"
    COMMUNICATION = "COMMUNICATION"
    DANGER = "DANGER"


class Episode(BaseModel):
    """A time-, place-, and importance-indexed personal event."""

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID
    episode_type: EpisodeType
    tick: int = Field(ge=0)
    x: int
    y: int
    summary: str = Field(min_length=1, max_length=500)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    participants: list[UUID] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class MessageType(StrEnum):
    """Initial forms of direct entity communication."""

    SPEECH = "SPEECH"
    KNOWLEDGE = "KNOWLEDGE"


class Message(BaseModel):
    """A delivered local message retained for later social systems."""

    id: UUID = Field(default_factory=uuid4)
    sender_id: UUID
    recipient_id: UUID
    message_type: MessageType
    tick: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=500)
    shared_records: dict[str, list[str]] = Field(default_factory=dict)
    transferred_count: int = Field(default=0, ge=0)
