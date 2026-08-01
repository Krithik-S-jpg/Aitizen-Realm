"""Application service for orchestrating the Simulation Engine.

Acts as a clean facade between external interfaces (API/WebSockets) and the core engine.
"""

import logging

from app.domain.interfaces.engine import ISimulationEngine
from app.domain.models.engine import EngineState, Tick

logger = logging.getLogger(__name__)


class EngineService:
    """Orchestrates the lifecycle and control of the simulation engine."""

    def __init__(self, engine: ISimulationEngine) -> None:
        """Initializes the EngineService.

        Args:
            engine: Concrete instance of the simulation engine interface.
        """
        self._engine = engine

    async def start_simulation(self) -> None:
        """Starts the simulation run loop."""
        logger.info("Application Request: Start Simulation")
        await self._engine.start()

    async def pause_simulation(self) -> None:
        """Pauses the simulation run loop."""
        logger.info("Application Request: Pause Simulation")
        await self._engine.pause()

    async def resume_simulation(self) -> None:
        """Resumes the simulation run loop."""
        logger.info("Application Request: Resume Simulation")
        await self._engine.resume()

    async def step_simulation(self) -> Tick:
        """Executes a single simulation tick.

        Returns:
            The Tick instance after the execution.
        """
        logger.info("Application Request: Step Simulation")
        return await self._engine.step()

    async def stop_simulation(self) -> None:
        """Stops the simulation run loop."""
        logger.info("Application Request: Stop Simulation")
        await self._engine.stop()

    def get_simulation_state(self) -> EngineState:
        """Gets the current state of the simulation.

        Returns:
            The current EngineState.
        """
        return self._engine.get_state()

    def get_current_tick(self) -> Tick:
        """Gets the current tick.

        Returns:
            The current Tick instance.
        """
        return self._engine.get_current_tick()

    def set_tick_rate(self, ticks_per_second: float) -> None:
        """Sets the simulation speed (ticks per second).

        Args:
            ticks_per_second: Number of ticks per second.
        """
        self._engine.set_tick_rate(ticks_per_second)

    def get_tick_rate(self) -> float:
        """Gets the current tick rate of the simulation.

        Returns:
            Current tick rate.
        """
        return self._engine.get_tick_rate()
