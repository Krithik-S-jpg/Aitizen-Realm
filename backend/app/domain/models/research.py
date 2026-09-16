"""Experiment configuration and reproducible simulation measurements."""

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExperimentStatus(StrEnum):
    """Lifecycle state for a configured simulation experiment."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class Experiment(BaseModel):
    """A reproducible named experiment and its controlled parameters."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    seed: int = Field(ge=0, le=2_147_483_647)
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at_tick: int = Field(default=0, ge=0)


class MetricsSnapshot(BaseModel):
    """One aggregate observation suitable for charts and comparisons."""

    tick: int = Field(ge=0)
    population: int = Field(ge=0)
    average_health: float = Field(ge=0.0, le=100.0)
    average_hunger: float = Field(ge=0.0, le=100.0)
    resources_available: float = Field(ge=0.0)
    structures: int = Field(ge=0)
    completed_structures: int = Field(ge=0)
    groups: int = Field(ge=0)
    communications: int = Field(ge=0)
