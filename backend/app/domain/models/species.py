"""Validated, data-driven animal life-history configuration."""

from pydantic import BaseModel, Field

from app.domain.models.calendar import Season


class SpeciesLifeHistory(BaseModel):
    """Biological parameters used by the shared wildlife lifecycle engine."""

    maturity_days: int = Field(gt=0)
    lifespan_days: int = Field(gt=0)
    gestation_days: int = Field(gt=0)
    litter_min: int = Field(gt=0)
    litter_max: int = Field(gt=0)
    breeding_seasons: set[Season]
    local_capacity: int = Field(gt=1)
    territory_radius: int = Field(gt=1)
    meat_yield: float = Field(gt=0)

    def model_post_init(self, __context: object) -> None:
        """Rejects configurations that cannot produce a valid litter."""
        if self.litter_max < self.litter_min:
            raise ValueError("litter_max must be greater than or equal to litter_min")
        if self.lifespan_days <= self.maturity_days:
            raise ValueError("lifespan_days must exceed maturity_days")
