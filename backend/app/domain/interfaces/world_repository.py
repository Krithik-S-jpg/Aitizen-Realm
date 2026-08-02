"""Abstract Interface for the World Repository.

Defines the contract for loading, persisting, and deleting World objects.
"""

from abc import ABC, abstractmethod

from app.domain.models.world import World


class IWorldRepository(ABC):
    """Interface specifying the operations of the World Repository."""

    @abstractmethod
    def get(self) -> World | None:
        """Retrieves the active World instance from the storage engine.

        Returns:
            The active World instance, or None if no world is currently active.
        """
        pass

    @abstractmethod
    def save(self, world: World) -> None:
        """Persists the active World instance to the storage engine.

        Args:
            world: The World instance to save.
        """
        pass

    @abstractmethod
    def delete(self) -> None:
        """Deletes/de-registers the active World instance from the storage engine."""
        pass
