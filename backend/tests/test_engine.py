"""Tests for the LoopEngine implementation."""

import asyncio

import pytest

from app.domain.interfaces.event_bus import IEventBus
from app.domain.models.engine import EngineState, Event
from app.infrastructure.engine.loop_engine import LoopEngine


@pytest.mark.asyncio
async def test_engine_initial_state(engine: LoopEngine) -> None:
    """Verifies that the engine is initialized with standard defaults."""
    assert engine.get_state() == EngineState.INITIALIZED
    assert engine.get_current_tick().value == 0
    assert engine.get_tick_rate() == 10.0


@pytest.mark.asyncio
async def test_engine_invalid_tick_rate(engine: LoopEngine) -> None:
    """Tests that setting an invalid tick rate raises an exception."""
    with pytest.raises(ValueError):
        engine.set_tick_rate(0)

    with pytest.raises(ValueError):
        engine.set_tick_rate(-5.0)


@pytest.mark.asyncio
async def test_engine_single_step(engine: LoopEngine, event_bus: IEventBus) -> None:
    """Tests that step() increments the tick and publishes lifecycle events."""
    published_events: list[Event] = []

    async def event_handler(event: Event) -> None:
        published_events.append(event)

    event_bus.subscribe("tick:started", event_handler)
    event_bus.subscribe("tick:completed", event_handler)

    # Step once
    new_tick = await engine.step()

    assert new_tick.value == 1
    assert engine.get_current_tick().value == 1

    # Verify that events were published
    assert len(published_events) == 2
    assert published_events[0].name == "tick:started"
    assert published_events[0].tick == 1
    assert published_events[1].name == "tick:completed"
    assert published_events[1].tick == 1


@pytest.mark.asyncio
async def test_engine_state_transitions(
    engine: LoopEngine, event_bus: IEventBus
) -> None:
    """Tests lifecycle states and matching event publishing."""
    events: list[str] = []

    async def log_event(event: Event) -> None:
        events.append(event.name)

    lifecycle_events = [
        "simulation:started",
        "simulation:paused",
        "simulation:resumed",
        "simulation:stopped",
    ]
    for name in lifecycle_events:
        event_bus.subscribe(name, log_event)

    # 1. Start
    await engine.start()
    assert engine.get_state() == EngineState.RUNNING
    assert "simulation:started" in events

    # 2. Pause
    await engine.pause()
    assert engine.get_state() == EngineState.PAUSED
    assert "simulation:paused" in events

    # 3. Resume
    await engine.resume()
    assert engine.get_state() == EngineState.RUNNING
    assert "simulation:resumed" in events

    # 4. Stop
    await engine.stop()
    assert engine.get_state() == EngineState.STOPPED
    assert "simulation:stopped" in events
    assert engine.get_current_tick().value == 0  # reset on stop


@pytest.mark.asyncio
async def test_engine_background_run(engine: LoopEngine, event_bus: IEventBus) -> None:
    """Tests that starting the engine runs the loop task in the background."""
    ticks: list[int] = []

    async def log_tick(event: Event) -> None:
        ticks.append(event.tick)

    event_bus.subscribe("tick:completed", log_tick)

    # Set high tick rate for quick testing
    engine.set_tick_rate(100.0)

    # Start loop
    await engine.start()
    await asyncio.sleep(0.05)  # Let it tick in the background

    await engine.stop()

    assert len(ticks) >= 1
    assert ticks[0] == 1


@pytest.mark.asyncio
async def test_engine_cannot_step_while_running(engine: LoopEngine) -> None:
    """Verifies that executing step() externally while running raises RuntimeError."""
    await engine.start()

    with pytest.raises(
        RuntimeError, match="Cannot manually step the simulation while it is running."
    ):
        await engine.step()

    await engine.stop()
