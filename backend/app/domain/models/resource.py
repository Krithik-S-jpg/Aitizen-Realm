"""Harvestable resource nodes owned by the simulation backend."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResourceType(StrEnum):
    """Initial resource categories available in the world."""

    TREE = "TREE"
    STONE = "STONE"
    PLANT = "PLANT"
    BUSH = "BUSH"
    MUSHROOM = "MUSHROOM"
    LOG = "LOG"
    STUMP = "STUMP"
    REEDS = "REEDS"
    LILY = "LILY"
    ORE = "ORE"
    CLAY = "CLAY"
    CACTUS = "CACTUS"
    HERB = "HERB"
    CARCASS = "CARCASS"


class ResourceNode(BaseModel):
    """A finite harvestable resource located on one world tile."""

    id: UUID = Field(default_factory=uuid4)
    resource_type: ResourceType
    x: int
    y: int
    quantity: float = Field(ge=0.0)
    capacity: float = Field(gt=0.0)
    regeneration_per_tick: float = Field(default=0.0, ge=0.0)
    growth: float = Field(default=1.0, ge=0.0, le=1.0)
    growth_per_tick: float = Field(default=0.0, ge=0.0)
    reserved_by: str | None = None
    reservation_expires_at: int | None = Field(default=None, ge=0)
    variant: int = Field(default=0, ge=0, le=7)
    produce_type: str | None = None
    produce_quantity: float = Field(default=0.0, ge=0.0)
    produce_capacity: float = Field(default=0.0, ge=0.0)
    produce_regeneration_per_tick: float = Field(default=0.0, ge=0.0)
    visual_state: str = "standing"
    state_changed_tick: int = Field(default=0, ge=0)

    def harvest(self, requested_amount: float) -> float:
        """Removes and returns up to the requested quantity."""
        if requested_amount <= 0.0:
            raise ValueError("Requested harvest amount must be greater than zero.")
        harvested = min(requested_amount, self.quantity)
        self.quantity -= harvested
        return harvested

    @property
    def depleted(self) -> bool:
        """Returns whether the node has no harvestable quantity remaining."""
        return self.quantity <= 0.0

    def advance_growth(self, environment_multiplier: float = 1.0) -> None:
        """Advances biological growth by one simulation tick."""
        if self.visual_state == "fallen":
            return
        if self.growth_per_tick > 0.0 and self.growth < 1.0:
            growth_delta = self.growth_per_tick * max(environment_multiplier, 0.0)
            self.growth = min(1.0, self.growth + growth_delta)
        if (
            self.regeneration_per_tick > 0.0
            and self.quantity < self.capacity
            and (self.growth_per_tick == 0.0 or self.growth >= 0.65)
        ):
            regenerated = self.regeneration_per_tick * max(environment_multiplier, 0.0)
            self.quantity = min(self.capacity, self.quantity + regenerated)
        if (
            self.produce_type is not None
            and self.growth >= 0.65
            and self.produce_quantity < self.produce_capacity
        ):
            produce = self.produce_regeneration_per_tick * max(
                environment_multiplier, 0.0
            )
            self.produce_quantity = min(
                self.produce_capacity, self.produce_quantity + produce
            )

    def pluck_produce(self, requested_amount: float) -> float:
        """Removes ripe renewable produce without damaging the parent node."""
        if self.produce_type is None:
            raise ValueError("Resource does not carry edible produce.")
        if requested_amount <= 0.0:
            raise ValueError("Requested amount must be greater than zero.")
        plucked = min(requested_amount, self.produce_quantity)
        if plucked <= 0.0:
            raise ValueError("No ripe produce is currently available.")
        self.produce_quantity -= plucked
        return plucked

    def reserve(self, actor_id: str, current_tick: int, duration_ticks: int) -> None:
        """Exclusively reserves this node for an actor for a bounded time."""
        if not actor_id.strip():
            raise ValueError("Actor ID cannot be empty.")
        if duration_ticks <= 0:
            raise ValueError("Reservation duration must be greater than zero.")
        if self.is_reserved(current_tick) and self.reserved_by != actor_id:
            raise ValueError("Resource is reserved by another actor.")
        self.reserved_by = actor_id
        self.reservation_expires_at = current_tick + duration_ticks

    def release(self, actor_id: str) -> None:
        """Releases a reservation owned by the given actor."""
        if self.reserved_by != actor_id:
            raise ValueError("Actor does not own this reservation.")
        self.reserved_by = None
        self.reservation_expires_at = None

    def is_reserved(self, current_tick: int) -> bool:
        """Returns whether a non-expired reservation currently exists."""
        if self.reserved_by is None or self.reservation_expires_at is None:
            return False
        if current_tick >= self.reservation_expires_at:
            self.reserved_by = None
            self.reservation_expires_at = None
            return False
        return True
