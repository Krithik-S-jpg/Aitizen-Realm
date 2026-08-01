"""In-memory event bus implementation.

Provides a lightweight, asyncio-compatible implementation of the IEventBus interface.
"""

import asyncio
import logging

from app.domain.interfaces.event_bus import EventHandler, IEventBus
from app.domain.models.engine import Event

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """An in-memory, asynchronous implementation of the IEventBus interface."""

    def __init__(self) -> None:
        """Initializes the InMemoryEventBus with empty subscribers dictionary."""
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Registers a handler for a specific event type.

        Args:
            event_name: The name of the event to listen for.
            handler: An async callback function to execute when the event occurs.
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if handler not in self._subscribers[event_name]:
            self._subscribers[event_name].append(handler)
            handler_name = (
                handler.__name__ if hasattr(handler, "__name__") else str(handler)
            )
            logger.debug(
                "Subscribed %s to event %s",
                handler_name,
                event_name,
            )

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Removes a previously registered event handler.

        Args:
            event_name: The name of the event type.
            handler: The callback function to remove.
        """
        if event_name in self._subscribers and handler in self._subscribers[event_name]:
            self._subscribers[event_name].remove(handler)
            handler_name = (
                handler.__name__ if hasattr(handler, "__name__") else str(handler)
            )
            logger.debug(
                "Unsubscribed %s from event %s",
                handler_name,
                event_name,
            )
            if not self._subscribers[event_name]:
                del self._subscribers[event_name]

    async def publish(self, event: Event) -> None:
        """Publishes an event to all registered subscribers concurrently.

        Each subscriber's callback is executed. Failures in one handler do not
        prevent other handlers from executing.

        Args:
            event: The Event instance to distribute.
        """
        handlers = self._subscribers.get(event.name, [])
        if not handlers:
            logger.debug(
                "Published event %s (tick %d) with 0 subscribers",
                event.name,
                event.tick,
            )
            return

        logger.debug(
            "Publishing event %s (tick %d) to %d subscribers",
            event.name,
            event.tick,
            len(handlers),
        )

        async def _safe_run(h: EventHandler) -> None:
            try:
                await h(event)
            except Exception as e:
                handler_name = h.__name__ if hasattr(h, "__name__") else str(h)
                logger.error(
                    "Error executing handler %s for event %s (id: %s): %s",
                    handler_name,
                    event.name,
                    event.id,
                    e,
                    exc_info=True,
                )

        # Run all subscribers concurrently
        await asyncio.gather(*[_safe_run(handler) for handler in handlers])
