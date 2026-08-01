"""Interface for the Task/Job Scheduler.

This module defines the abstract base class for scheduling deferred or recurring
tasks to be executed at precise future simulation ticks.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.domain.models.engine import ScheduledTask

# Type alias for task execution callbacks
TaskExecutor = Callable[[ScheduledTask], Awaitable[None]]


class IScheduler(ABC):
    """Abstract Base Class for scheduling and running future-tick actions."""

    @abstractmethod
    def schedule(
        self,
        name: str,
        target_tick: int,
        executor: TaskExecutor,
        payload: dict[str, Any] | None = None,
        is_recurring: bool = False,
        interval_ticks: int = 0,
    ) -> ScheduledTask:
        """Schedules a new task for execution.

        Args:
            name: Descriptive name of the task.
            target_tick: The simulation tick at which the task should run.
            executor: The async callback that runs the task.
            payload: Optional parameters for task execution.
            is_recurring: True if the task repeats after execution.
            interval_ticks: The repetition interval in ticks.

        Returns:
            The created ScheduledTask instance.
        """
        pass

    @abstractmethod
    async def process_tick(self, current_tick: int) -> None:
        """Executes all tasks scheduled for the current tick.

        Args:
            current_tick: The active simulation tick.
        """
        pass

    @abstractmethod
    def cancel(self, task_id: UUID) -> bool:
        """Cancels a scheduled task by ID.

        Args:
            task_id: The UUID of the scheduled task.

        Returns:
            True if the task was found and cancelled, False otherwise.
        """
        pass

    @abstractmethod
    def get_all_scheduled_tasks(self) -> list[ScheduledTask]:
        """Retrieves a list of all currently scheduled tasks.

        Returns:
            A list of ScheduledTask instances.
        """
        pass
