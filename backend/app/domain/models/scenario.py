"""Versioned, bounded scenario documents; no executable scripts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Objective(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=120)
    metric: Literal["elapsed", "population", "structures", "inventory", "explored"]
    target: float = Field(gt=0, le=1000000)
    subject: str = Field(default="", max_length=64)


class ScenarioEvent(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    at_tick: int = Field(default=0, ge=0, le=1000000)
    after_objective: str = Field(default="", max_length=64)
    kind: Literal["resource", "weather", "message"]
    choice: str = Field(default="", max_length=64)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    radius: int = Field(default=0, ge=0, le=2)
    message: str = Field(default="", max_length=500)
    on_blocked: Literal["skip", "fail"] = "skip"


class ScenarioDefinition(StrictModel):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    deadline: int = Field(default=0, ge=0, le=1000000)
    minimum_population: int = Field(default=0, ge=0, le=10000)
    objectives: list[Objective] = Field(min_length=1, max_length=32)
    events: list[ScenarioEvent] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_links(self):
        for entries in (self.objectives, self.events):
            if len({entry.id for entry in entries}) != len(entries):
                raise ValueError("Objective and event IDs must be unique within their lists.")
        ids = {goal.id for goal in self.objectives}
        for event in self.events:
            if event.after_objective and event.after_objective not in ids:
                raise ValueError("Event refers to an unknown objective.")
            if event.kind == "resource" and event.choice not in {"TREE", "STONE", "BUSH", "HERB", "ORE"}:
                raise ValueError("Unsupported resource event.")
            if event.kind == "weather" and event.choice not in {"RAIN", "SNOW", "CLEAR"}:
                raise ValueError("Unsupported weather event.")
        from app.domain.models.structure import StructureType
        for goal in self.objectives:
            if goal.metric == "structures" and goal.subject and goal.subject not in {s.value for s in StructureType}:
                raise ValueError("Unknown structure type; use uppercase or blank for all.")
            if goal.metric == "inventory" and not goal.subject.strip():
                raise ValueError("Inventory goals require an item name, e.g. wood.")
        return self
