"""Actor-owned carried materials, independent of the future entity model."""

from pydantic import BaseModel, Field


class Inventory(BaseModel):
    """A weight-limited collection of raw simulation materials."""

    capacity: float = Field(default=50.0, gt=0.0)
    items: dict[str, float] = Field(default_factory=dict)

    @property
    def carried(self) -> float:
        """Returns the inventory's currently used capacity."""
        return sum(self.items.values())

    def add(self, item_type: str, amount: float) -> float:
        """Adds as much as fits and returns the accepted amount."""
        if amount <= 0.0:
            raise ValueError("Amount must be greater than zero.")
        accepted = min(amount, max(0.0, self.capacity - self.carried))
        if accepted > 0.0:
            self.items[item_type] = self.items.get(item_type, 0.0) + accepted
        return accepted

    def has(self, requirements: dict[str, float]) -> bool:
        """Checks whether every requested material is available."""
        return all(
            self.items.get(item, 0.0) >= amount for item, amount in requirements.items()
        )

    def consume(self, requirements: dict[str, float]) -> None:
        """Atomically removes a complete material recipe."""
        if not self.has(requirements):
            raise ValueError("Inventory does not contain the required materials.")
        for item, amount in requirements.items():
            remaining = self.items[item] - amount
            if remaining <= 0.0:
                self.items.pop(item, None)
            else:
                self.items[item] = remaining
