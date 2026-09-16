"""Physiological and environmental state for living entities."""

from pydantic import BaseModel, Field


class NeedsState(BaseModel):
    """Normalized survival pressures and body condition."""

    hunger: float = Field(default=0.0, ge=0.0, le=100.0)
    thirst: float = Field(default=0.0, ge=0.0, le=100.0)
    energy: float = Field(default=100.0, ge=0.0, le=100.0)
    body_temperature_c: float = Field(default=37.0, ge=25.0, le=45.0)
    safety: float = Field(default=100.0, ge=0.0, le=100.0)
    health: float = Field(default=100.0, ge=0.0, le=100.0)

    @property
    def critical(self) -> bool:
        """Returns whether any survival pressure has reached danger level."""
        return (
            self.hunger >= 85.0
            or self.thirst >= 85.0
            or self.energy <= 15.0
            or not 35.0 <= self.body_temperature_c <= 39.0
            or self.safety <= 20.0
            or self.health <= 25.0
        )

    def advance(
        self,
        ambient_temperature_c: float,
        exposure: float = 1.0,
        exertion: float = 0.0,
    ) -> None:
        """Advances needs by one simulation tick with environmental exposure."""
        self.hunger = min(100.0, self.hunger + 0.16 + exertion * 0.06)
        self.thirst = min(100.0, self.thirst + 0.24 + exertion * 0.10)
        self.energy = max(0.0, self.energy - 0.10 - exertion * 0.20)
        temperature_pull = (ambient_temperature_c - 20.0) * 0.004 * max(exposure, 0.0)
        self.body_temperature_c = min(
            45.0, max(25.0, self.body_temperature_c + temperature_pull)
        )
        unsafe_temperature = max(0.0, abs(self.body_temperature_c - 37.0) - 1.5)
        self.safety = max(0.0, self.safety - unsafe_temperature * 0.08)
        survival_damage = max(0.0, self.hunger - 92.0) * 0.025
        survival_damage += max(0.0, self.thirst - 90.0) * 0.04
        survival_damage += unsafe_temperature * 0.03
        self.health = max(0.0, self.health - survival_damage)

    def eat(self, nutrition: float, healing: float = 0.0) -> None:
        """Reduces hunger and applies bounded food recovery."""
        if nutrition <= 0.0:
            raise ValueError("Nutrition must be greater than zero.")
        self.hunger = max(0.0, self.hunger - nutrition)
        self.health = min(100.0, self.health + max(healing, 0.0))

    def drink(self, hydration: float) -> None:
        """Reduces thirst by the supplied hydration."""
        if hydration <= 0.0:
            raise ValueError("Hydration must be greater than zero.")
        self.thirst = max(0.0, self.thirst - hydration)

    def rest(self, recovery: float) -> None:
        """Restores bounded energy."""
        if recovery <= 0.0:
            raise ValueError("Recovery must be greater than zero.")
        self.energy = min(100.0, self.energy + recovery)
