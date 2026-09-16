"""Inspectable goals, actions, and utility-based decision records."""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GoalType(StrEnum):
    """Initial motives available to autonomous entities."""

    SATISFY_HUNGER = "SATISFY_HUNGER"
    SATISFY_THIRST = "SATISFY_THIRST"
    REST = "REST"
    SEEK_SAFETY = "SEEK_SAFETY"
    GATHER = "GATHER"
    CRAFT = "CRAFT"
    BUILD = "BUILD"
    EXPLORE = "EXPLORE"


class ActionType(StrEnum):
    """Executable actions selected to pursue goals."""

    EAT = "EAT"
    DRINK = "DRINK"
    REST = "REST"
    MOVE = "MOVE"
    GATHER = "GATHER"
    CHOP = "CHOP"
    PLUCK = "PLUCK"
    CRAFT = "CRAFT"
    BUILD = "BUILD"
    OBSERVE = "OBSERVE"
    IDLE = "IDLE"


class TaskStatus(StrEnum):
    """Shared lifecycle for goals and actions."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Goal(BaseModel):
    """A utility-selected desired outcome."""

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID
    goal_type: GoalType
    status: TaskStatus = TaskStatus.PENDING
    utility_score: float = Field(ge=0.0)
    created_at_tick: int = Field(ge=0)
    completed_at_tick: int | None = Field(default=None, ge=0)
    reason: str
    target: dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    """One inspectable operation used to pursue a goal."""

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID
    goal_id: UUID
    action_type: ActionType
    status: TaskStatus = TaskStatus.PENDING
    created_at_tick: int = Field(ge=0)
    completed_at_tick: int | None = Field(default=None, ge=0)
    target: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None
    progress: float = Field(default=0.0, ge=0.0)
    work_required: float = Field(default=0.0, ge=0.0)

    @property
    def progress_ratio(self) -> float:
        """Returns normalized work completion for timed actions."""
        if self.work_required <= 0.0:
            return 1.0
        return min(1.0, self.progress / self.work_required)


class UtilityOption(BaseModel):
    """A scored candidate retained for decision explainability."""

    goal_type: GoalType
    score: float = Field(ge=0.0)
    reason: str
