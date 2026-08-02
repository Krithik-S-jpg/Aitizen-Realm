"""In-memory implementation of the World Repository.

Provides thread-safe access to a temporary in-memory World instance,
matching the IWorldRepository contract.
"""

import threading

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.world import World


class InMemoryWorldRepository(IWorldRepository):
    """Temporary in-memory adapter implementing IWorldRepository."""

    def __init__(self) -> None:
        """Initializes the InMemoryWorldRepository with thread safety."""
        self._world: World | None = None
        self._lock = threading.Lock()

    def get(self) -> World | None:
        """Retrieves the active World instance.

        Returns:
            The active World instance, or None if not set.
        """
        with self._lock:
            return self._world

    def save(self, world: World) -> None:
        """Persists the active World instance.

        Args:
            world: The World instance to save.
        """
        with self._lock:
            self._world = world

    def delete(self) -> None:
        """Deletes/de-registers the active World instance."""
        with self._lock:
            self._world = None
