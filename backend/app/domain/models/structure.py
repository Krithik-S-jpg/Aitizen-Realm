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
    ROAD = "ROAD"


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
    materials_required: dict[str, float] = Field(default_factory=dict)
    materials_delivered: dict[str, float] = Field(default_factory=dict)
    bed_capacity: int = Field(default=0, ge=0)
    resident_ids: list[str] = Field(default_factory=list)
    planted: bool = False
    watered: bool = False
    last_tended_tick: int | None = Field(default=None, ge=0)

    @property
    def completed(self) -> bool:
        """Returns whether all required construction work is finished."""
        return self.progress >= self.work_required

    @property
    def funded(self) -> bool:
        """Returns whether every construction material reached the site."""
        return all(
            self.materials_delivered.get(material, 0.0) >= amount
            for material, amount in self.materials_required.items()
        )

    @property
    def missing_materials(self) -> dict[str, float]:
        """Returns positive material deficits remaining at this site."""
        return {
            material: missing
            for material, required in self.materials_required.items()
            if (missing := required - self.materials_delivered.get(material, 0.0)) > 0.0
        }

    def apply_work(self, amount: float) -> float:
        """Applies work without exceeding the blueprint requirement."""
        if amount <= 0.0:
            raise ValueError("Work amount must be greater than zero.")
        applied = min(amount, self.work_required - self.progress)
        self.progress += applied
        return applied
