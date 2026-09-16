"""Generic world entities and their persistent limited knowledge."""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.models.needs import NeedsState
from app.domain.models.society import Profession


class EntityKind(StrEnum):
    """Broad entity categories shared by future simulation systems."""

    AGENT = "AGENT"
    ANIMAL = "ANIMAL"
    OBJECT = "OBJECT"


class Entity(BaseModel):
    """A backend-owned identity positioned in persistent world coordinates."""

    id: UUID = Field(default_factory=uuid4)
    kind: EntityKind
    name: str = Field(min_length=1, max_length=80)
    x: int
    y: int
    perception_radius: int = Field(default=6, ge=1, le=32)
    active: bool = True
    tags: set[str] = Field(default_factory=set)
    metadata: dict[str, Any] = Field(default_factory=dict)
    needs: NeedsState | None = None
    profession: Profession = Profession.GENERALIST
    skills: dict[str, float] = Field(default_factory=dict)
    group_id: UUID | None = None

    def distance_squared_to(self, x: int, y: int) -> int:
        """Returns squared tile distance without floating-point operations."""
        return (self.x - x) ** 2 + (self.y - y) ** 2


class KnowledgeRecord(BaseModel):
    """The last observation an entity retained about one world object."""

    key: str
    category: str
    x: int
    y: int
    last_seen_tick: int = Field(ge=0)
    first_seen_tick: int = Field(default=0, ge=0)
    observation_count: int = Field(default=1, ge=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_entity_id: UUID | None = None
    learned_at_tick: int | None = Field(default=None, ge=0)
    data: dict[str, Any] = Field(default_factory=dict)

    def refresh(self, tick: int, data: dict[str, Any]) -> None:
        """Refreshes a direct observation and restores full confidence."""
        self.last_seen_tick = tick
        self.learned_at_tick = tick
        self.observation_count += 1
        self.confidence = 1.0
        self.source_entity_id = None
        self.data = data


class EntityKnowledge(BaseModel):
    """An entity's private, incomplete representation of the world."""

    observer_id: UUID
    last_observation_tick: int = Field(default=0, ge=0)
    tiles: dict[str, KnowledgeRecord] = Field(default_factory=dict)
    resources: dict[str, KnowledgeRecord] = Field(default_factory=dict)
    structures: dict[str, KnowledgeRecord] = Field(default_factory=dict)
    entities: dict[str, KnowledgeRecord] = Field(default_factory=dict)
