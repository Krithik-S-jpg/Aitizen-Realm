"""Interface for the Event Bus.

This module defines the abstract base class for event distribution
within the simulation platform to ensure loose coupling.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.domain.models.engine import Event

# Type alias for event handler callbacks
EventHandler = Callable[[Event], Awaitable[None]]


class IEventBus(ABC):
    """Abstract Base Class for the event subscription and dispatching system."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publishes an event to all registered subscribers.

        Args:
            event: The Event instance to distribute.
        """
        pass

    @abstractmethod
    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Registers a handler for a specific event type.

        Args:
            event_name: The name of the event to listen for.
            handler: An async callback function to execute when the event occurs.
        """
        pass

    @abstractmethod
    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Removes a previously registered event handler.

        Args:
            event_name: The name of the event type.
            handler: The callback function to remove.
        """
        pass
