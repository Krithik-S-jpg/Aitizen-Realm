"""Tests for core domain models."""

import time
from uuid import UUID

from app.domain.models.engine import EngineState, Event, ScheduledTask, Tick


def test_engine_state_enum() -> None:
    """Verifies that EngineState values are mapped correctly."""
    assert EngineState.INITIALIZED == "INITIALIZED"
    assert EngineState.RUNNING == "RUNNING"
    assert EngineState.PAUSED == "PAUSED"
    assert EngineState.STOPPED == "STOPPED"


def test_tick_model() -> None:
    """Verifies Tick construction and progression."""
    now = time.time()
    tick = Tick(value=5, timestamp=now)

    assert tick.value == 5
    assert tick.timestamp == now

    # Test progression
    future_time = now + 1.0
    next_tick = tick.next_tick(future_time)

    assert next_tick.value == 6
    assert next_tick.timestamp == future_time


def test_event_model() -> None:
    """Verifies Event initialization and default values."""
    now = time.time()
    event = Event(name="test:event", tick=2, timestamp=now, payload={"key": "val"})

    assert isinstance(event.id, UUID)
    assert event.name == "test:event"
    assert event.tick == 2
    assert event.timestamp == now
    assert event.payload == {"key": "val"}

    # Test default payload is empty dict
    event_default = Event(name="test:default", tick=0, timestamp=now)
    assert event_default.payload == {}


def test_scheduled_task_model() -> None:
    """Verifies ScheduledTask configuration and defaults."""
    task = ScheduledTask(name="test_task", target_tick=10)

    assert isinstance(task.id, UUID)
    assert task.name == "test_task"
    assert task.target_tick == 10
    assert task.payload == {}
    assert not task.is_recurring
    assert task.interval_ticks == 0

    # Recurring configuration
    recurring = ScheduledTask(
        name="recurring_task",
        target_tick=5,
        payload={"param": 42},
        is_recurring=True,
        interval_ticks=10,
    )
    assert recurring.is_recurring
    assert recurring.interval_ticks == 10
    assert recurring.payload == {"param": 42}
