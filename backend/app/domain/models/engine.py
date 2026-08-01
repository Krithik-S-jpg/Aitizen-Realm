"""Domain models for the Simulation Engine Core.

This module defines the basic entities and value objects that represent
the state, time, events, and tasks of the simulation.
"""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EngineState(StrEnum):
    """Enumeration of the possible states of the simulation engine."""

    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class Tick(BaseModel):
    """Represents a specific point in simulation time (discrete unit of time)."""

    value: int = Field(ge=0, description="The sequential tick number, starting at 0")
    timestamp: float = Field(
        description="The real-world UNIX timestamp when this tick occurred"
    )

    def next_tick(self, timestamp: float) -> "Tick":
        """Generate the next tick with the given real-world timestamp.

        Args:
            timestamp: The real-world UNIX timestamp for the new tick.

        Returns:
            A new Tick instance with incremented value.
        """
        return Tick(value=self.value + 1, timestamp=timestamp)


class Event(BaseModel):
    """Base class for all domain and system events within the simulation."""

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this event"
    )
    name: str = Field(description="The unique name identifying the event type")
    tick: int = Field(
        ge=0, description="The simulation tick during which the event occurred"
    )
    timestamp: float = Field(description="The real-world UNIX timestamp of the event")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary parameters of the event"
    )


class ScheduledTask(BaseModel):
    """Represents a registered task scheduled to run in the future."""

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this scheduled task",
    )
    name: str = Field(description="Descriptive name of the task")
    target_tick: int = Field(
        ge=0,
        description="The target simulation tick when this task should execute",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary task payload parameters"
    )
    is_recurring: bool = Field(
        default=False, description="Whether this task should repeat"
    )
    interval_ticks: int = Field(
        default=0, ge=0, description="The interval in ticks for recurrence"
    )
