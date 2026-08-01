"""Asynchronous loop implementation of the Simulation Engine.

Drives the simulation timeline and orchestrates event and task processing.
"""

import asyncio
import logging
import time

from app.domain.interfaces.engine import ISimulationEngine
from app.domain.interfaces.event_bus import IEventBus
from app.domain.interfaces.scheduler import IScheduler
from app.domain.models.engine import EngineState, Event, Tick

logger = logging.getLogger(__name__)


class LoopEngine(ISimulationEngine):
    """An asyncio background-task simulation engine implementation."""

    def __init__(
        self,
        event_bus: IEventBus,
        scheduler: IScheduler,
        ticks_per_second: float = 1.0,
    ) -> None:
        """Initializes the LoopEngine.

        Args:
            event_bus: The Event Bus interface instance.
            scheduler: The Scheduler interface instance.
            ticks_per_second: Ticks to execute per real second (defaults to 1.0).
        """
        self._event_bus = event_bus
        self._scheduler = scheduler
        self._ticks_per_second = ticks_per_second
        self._state = EngineState.INITIALIZED
        self._current_tick = Tick(value=0, timestamp=time.time())
        self._loop_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    def get_state(self) -> EngineState:
        """Gets the current state of the engine.

        Returns:
            The EngineState enum value.
        """
        return self._state

    def get_current_tick(self) -> Tick:
        """Gets the current simulation tick.

        Returns:
            The current Tick instance.
        """
        return self._current_tick

    def set_tick_rate(self, ticks_per_second: float) -> None:
        """Sets the execution rate of the simulation loop.

        Args:
            ticks_per_second: Number of ticks to execute per real-world second.
        """
        if ticks_per_second <= 0:
            raise ValueError("Tick rate must be greater than zero.")
        self._ticks_per_second = ticks_per_second
        logger.info("Simulation tick rate set to %.2f ticks/sec", ticks_per_second)

    def get_tick_rate(self) -> float:
        """Gets the current simulation execution rate.

        Returns:
            Number of ticks executing per real-world second.
        """
        return self._ticks_per_second

    async def start(self) -> None:
        """Starts the simulation loop, running it in the background."""
        async with self._lock:
            if self._state == EngineState.RUNNING:
                logger.warning("Simulation is already running.")
                return

            self._state = EngineState.RUNNING
            logger.info("Starting simulation...")
            await self._event_bus.publish(
                Event(
                    name="simulation:started",
                    tick=self._current_tick.value,
                    timestamp=time.time(),
                    payload={"tick_rate": self._ticks_per_second},
                )
            )

            if not self._loop_task or self._loop_task.done():
                self._loop_task = asyncio.create_task(self._run_loop())

    async def pause(self) -> None:
        """Pauses the simulation, keeping current time and state."""
        async with self._lock:
            if self._state != EngineState.RUNNING:
                logger.warning("Simulation can only be paused from RUNNING state.")
                return

            self._state = EngineState.PAUSED
            logger.info("Simulation paused at tick %d", self._current_tick.value)
            await self._event_bus.publish(
                Event(
                    name="simulation:paused",
                    tick=self._current_tick.value,
                    timestamp=time.time(),
                )
            )

    async def resume(self) -> None:
        """Resumes the simulation if paused."""
        async with self._lock:
            if self._state != EngineState.PAUSED:
                logger.warning("Simulation can only be resumed from PAUSED state.")
                return

            self._state = EngineState.RUNNING
            logger.info("Simulation resumed at tick %d", self._current_tick.value)
            await self._event_bus.publish(
                Event(
                    name="simulation:resumed",
                    tick=self._current_tick.value,
                    timestamp=time.time(),
                )
            )

            if not self._loop_task or self._loop_task.done():
                self._loop_task = asyncio.create_task(self._run_loop())

    async def step(self) -> Tick:
        """Executes a single tick of the simulation synchronously.

        This is useful for debugging or step-by-step external control.

        Returns:
            The updated Tick instance after execution.
        """
        if (
            self._state == EngineState.RUNNING
            and asyncio.current_task() != self._loop_task
        ):
            raise RuntimeError(
                "Cannot manually step the simulation while it is running."
            )

        # Execute tick increment and associated processing
        next_t = Tick(value=self._current_tick.value + 1, timestamp=time.time())
        self._current_tick = next_t

        logger.debug("Processing simulation tick %d", next_t.value)

        # 1. Dispatch "tick:started" event
        await self._event_bus.publish(
            Event(
                name="tick:started",
                tick=next_t.value,
                timestamp=next_t.timestamp,
            )
        )

        # 2. Process all pending tasks in the Scheduler
        await self._scheduler.process_tick(next_t.value)

        # 3. Dispatch "tick:completed" event
        await self._event_bus.publish(
            Event(
                name="tick:completed",
                tick=next_t.value,
                timestamp=time.time(),
            )
        )

        return next_t

    async def stop(self) -> None:
        """Stops the simulation, resetting the tick counter and state."""
        async with self._lock:
            if self._state == EngineState.STOPPED:
                logger.warning("Simulation is already stopped.")
                return

            self._state = EngineState.STOPPED
            logger.info("Stopping simulation...")
            await self._event_bus.publish(
                Event(
                    name="simulation:stopped",
                    tick=self._current_tick.value,
                    timestamp=time.time(),
                )
            )

            # Cancel background task
            if self._loop_task and not self._loop_task.done():
                self._loop_task.cancel()
                try:
                    await self._loop_task
                except asyncio.CancelledError:
                    pass
                self._loop_task = None

            # Reset tick counter
            self._current_tick = Tick(value=0, timestamp=time.time())

    async def _run_loop(self) -> None:
        """The core internal asyncio run loop."""
        try:
            while self._state == EngineState.RUNNING:
                start_time = asyncio.get_event_loop().time()

                # Step the simulation
                await self.step()

                # Calculate sleep duration to maintain tick rate
                tick_interval = 1.0 / self._ticks_per_second
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_duration = max(0.0, tick_interval - elapsed)

                await asyncio.sleep(sleep_duration)
        except asyncio.CancelledError:
            logger.debug("Simulation loop task cancelled.")
        except Exception as e:
            logger.error("Error in simulation loop: %s", e, exc_info=True)
            self._state = EngineState.STOPPED
