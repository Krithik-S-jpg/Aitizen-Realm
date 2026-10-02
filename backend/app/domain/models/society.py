"""Persistent social bonds, professions, and emergent groups."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Profession(StrEnum):
    """Roles inferred from an agent's accumulated practical experience."""

    GENERALIST = "GENERALIST"
    FORAGER = "FORAGER"
    WOODCUTTER = "WOODCUTTER"
    MINER = "MINER"
    BUILDER = "BUILDER"
    CRAFTER = "CRAFTER"
    EXPLORER = "EXPLORER"


class SocialBond(BaseModel):
    """Directional relationship values formed through repeated interaction."""

    source_id: UUID
    target_id: UUID
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)
    familiarity: float = Field(default=0.0, ge=0.0, le=1.0)
    interactions: int = Field(default=0, ge=0)
    last_interaction_tick: int = Field(default=0, ge=0)

    def interact(self, tick: int, trust_delta: float = 0.02) -> None:
        """Updates the bond from one direct social encounter."""
        self.interactions += 1
        self.last_interaction_tick = tick
        self.familiarity = min(1.0, self.familiarity + 0.04)
        self.trust = min(1.0, max(-1.0, self.trust + trust_delta))


class SocialGroup(BaseModel):
    """A persistent agent group with membership and a shared home coordinate."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    founder_id: UUID
    member_ids: list[UUID]
    home_x: int
    home_y: int
    formed_at_tick: int = Field(ge=0)
    shared_resources: dict[str, float] = Field(default_factory=dict)


class Household(BaseModel):
    """Citizens sharing one completed home and its finite beds."""

    id: UUID = Field(default_factory=uuid4)
    group_id: UUID
    home_structure_id: UUID
    member_ids: list[UUID] = Field(default_factory=list)
    bed_capacity: int = Field(ge=1)
    created_at_tick: int = Field(ge=0)


class SettlementJob(BaseModel):
    """A persistent, inspectable request claimed by at most one citizen."""

    id: UUID = Field(default_factory=uuid4)
    group_id: UUID | None = None
    job_type: str = Field(min_length=1, max_length=48)
    target_id: str | None = None
    material: str | None = None
    amount: float = Field(default=0.0, ge=0.0)
    priority: float = Field(default=0.5, ge=0.0, le=2.0)
    reason: str
    created_at_tick: int = Field(ge=0)
    claimed_by: UUID | None = None
    claimed_at_tick: int | None = Field(default=None, ge=0)
    status: str = "open"
