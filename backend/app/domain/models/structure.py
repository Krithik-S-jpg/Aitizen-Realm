"""Construction sites and completed world structures."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.models.inventory import Inventory


class StructureType(StrEnum):
    """Buildable structure blueprints."""

    CAMPFIRE = "CAMPFIRE"
    SHELTER = "SHELTER"
    STORAGE = "STORAGE"
    TENT = "TENT"
    WORKBENCH = "WORKBENCH"
    WELL = "WELL"
    TORCH = "TORCH"
    FENCE = "FENCE"
    FARM = "FARM"


class Structure(BaseModel):
    """A placed construction site that can become operational."""

    id: UUID = Field(default_factory=uuid4)
    structure_type: StructureType
    x: int
    y: int
    builder_id: str
    progress: float = Field(default=0.0, ge=0.0)
    work_required: float = Field(gt=0.0)
    stockpile: Inventory = Field(default_factory=lambda: Inventory(capacity=500.0))
    fuel: float = Field(default=0.0, ge=0.0)
    crop_growth: float = Field(default=0.0, ge=0.0, le=1.0)
    crop_food: float = Field(default=0.0, ge=0.0)

    @property
    def completed(self) -> bool:
        """Returns whether all required construction work is finished."""
        return self.progress >= self.work_required

    def apply_work(self, amount: float) -> float:
        """Applies work without exceeding the blueprint requirement."""
        if amount <= 0.0:
            raise ValueError("Work amount must be greater than zero.")
        applied = min(amount, self.work_required - self.progress)
        self.progress += applied
        return applied
