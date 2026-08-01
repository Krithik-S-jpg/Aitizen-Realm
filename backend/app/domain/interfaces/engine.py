"""Interface for the Simulation Engine.

This module defines the abstract base class that controls the core run loop,
tick progression, and state transitions of the simulation.
"""

from abc import ABC, abstractmethod

from app.domain.models.engine import EngineState, Tick


class ISimulationEngine(ABC):
    """Abstract Base Class for the central orchestrator of the simulation."""

    @abstractmethod
    def get_state(self) -> EngineState:
        """Gets the current state of the engine.

        Returns:
            The EngineState enum value.
        """
        pass

    @abstractmethod
    def get_current_tick(self) -> Tick:
        """Gets the current simulation tick.

        Returns:
            The current Tick instance.
        """
        pass

    @abstractmethod
    def set_tick_rate(self, ticks_per_second: float) -> None:
        """Sets the execution rate of the simulation loop.

        Args:
            ticks_per_second: Number of ticks to execute per real-world second.
        """
        pass

    @abstractmethod
    def get_tick_rate(self) -> float:
        """Gets the current simulation execution rate.

        Returns:
            Number of ticks executing per real-world second.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Starts the simulation loop, running it in the background."""
        pass

    @abstractmethod
    async def pause(self) -> None:
        """Pauses the simulation, keeping current time and state."""
        pass

    @abstractmethod
    async def resume(self) -> None:
        """Resumes the simulation if paused."""
        pass

    @abstractmethod
    async def step(self) -> Tick:
        """Executes a single tick of the simulation synchronously.

        This is useful for debugging or step-by-step external control.

        Returns:
            The updated Tick instance after execution.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stops the simulation, resetting the tick counter and state."""
        pass
