"""Tests for the InMemoryEventBus implementation."""

import time

import pytest

from app.domain.interfaces.event_bus import IEventBus
from app.domain.models.engine import Event


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish(event_bus: IEventBus) -> None:
    """Tests that a subscribed callback is executed upon publishing an event."""
    received_events: list[Event] = []

    async def mock_handler(event: Event) -> None:
        received_events.append(event)

    event_bus.subscribe("test:event", mock_handler)

    test_event = Event(name="test:event", tick=1, timestamp=time.time())
    await event_bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].id == test_event.id
    assert received_events[0].name == "test:event"


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers(event_bus: IEventBus) -> None:
    """Tests that multiple subscribers receive the published event concurrently."""
    tracker: list[str] = []

    async def handler_one(event: Event) -> None:
        tracker.append("one")

    async def handler_two(event: Event) -> None:
        tracker.append("two")

    event_bus.subscribe("multi:event", handler_one)
    event_bus.subscribe("multi:event", handler_two)

    test_event = Event(name="multi:event", tick=0, timestamp=time.time())
    await event_bus.publish(test_event)

    assert "one" in tracker
    assert "two" in tracker
    assert len(tracker) == 2


@pytest.mark.asyncio
async def test_event_bus_unsubscribe(event_bus: IEventBus) -> None:
    """Tests that unsubscribed handlers are no longer triggered."""
    received_count = 0

    async def mock_handler(event: Event) -> None:
        nonlocal received_count
        received_count += 1

    event_bus.subscribe("unsub:event", mock_handler)

    # First publish
    await event_bus.publish(Event(name="unsub:event", tick=1, timestamp=time.time()))
    assert received_count == 1

    # Unsubscribe
    event_bus.unsubscribe("unsub:event", mock_handler)

    # Second publish
    await event_bus.publish(Event(name="unsub:event", tick=2, timestamp=time.time()))
    assert received_count == 1  # Should still be 1


@pytest.mark.asyncio
async def test_event_bus_error_isolation(event_bus: IEventBus) -> None:
    """Tests that errors in one handler do not disrupt other handlers."""
    tracker: list[str] = []

    async def failing_handler(event: Event) -> None:
        raise ValueError("Simulated handler crash")

    async def succeeding_handler(event: Event) -> None:
        tracker.append("success")

    event_bus.subscribe("crash:event", failing_handler)
    event_bus.subscribe("crash:event", succeeding_handler)

    # Should execute both (and log the failure of the first) without throwing
    await event_bus.publish(Event(name="crash:event", tick=1, timestamp=time.time()))

    assert tracker == ["success"]
