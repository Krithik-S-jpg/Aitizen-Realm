"""Planned backend-controlled movement through world tiles."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MovementStatus(StrEnum):
    """Current execution state of a planned route."""

    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class MovementPlan(BaseModel):
    """A route whose steps are applied only by authoritative ticks."""

    entity_id: UUID
    destination_x: int
    destination_y: int
    path: list[tuple[int, int]] = Field(min_length=1)
    next_step_index: int = Field(default=1, ge=1)
    status: MovementStatus = MovementStatus.MOVING
    planned_at_tick: int = Field(ge=0)
    last_advanced_tick: int | None = Field(default=None, ge=0)

    @property
    def remaining_steps(self) -> int:
        """Returns the number of unapplied route coordinates."""
        return max(0, len(self.path) - self.next_step_index)
