"""In-memory task scheduler implementation.

Provides a precise scheduler matching tasks to simulation ticks.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.domain.interfaces.scheduler import IScheduler, TaskExecutor
from app.domain.models.engine import ScheduledTask

logger = logging.getLogger(__name__)


class MemoryScheduler(IScheduler):
    """An in-memory, thread-safe task scheduler based on simulation ticks."""

    def __init__(self) -> None:
        """Initializes the MemoryScheduler with empty task pools."""
        self._tasks: dict[UUID, ScheduledTask] = {}
        self._executors: dict[UUID, TaskExecutor] = {}

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
        task = ScheduledTask(
            name=name,
            target_tick=target_tick,
            payload=payload or {},
            is_recurring=is_recurring,
            interval_ticks=interval_ticks,
        )
        self._tasks[task.id] = task
        self._executors[task.id] = executor

        logger.debug(
            "Scheduled task %s (id: %s) for tick %d",
            name,
            task.id,
            target_tick,
        )
        return task

    async def process_tick(self, current_tick: int) -> None:
        """Executes all tasks scheduled for current_tick or earlier.

        Also handles rescheduling of recurring tasks.

        Args:
            current_tick: The active simulation tick.
        """
        # Find all tasks to execute (target_tick <= current_tick)
        pending_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task.target_tick <= current_tick
        ]

        if not pending_ids:
            return

        logger.debug(
            "Scheduler processing %d tasks at tick %d",
            len(pending_ids),
            current_tick,
        )

        tasks_to_run = [self._tasks[tid] for tid in pending_ids]

        async def _safe_execute(task: ScheduledTask) -> None:
            executor = self._executors.get(task.id)
            if not executor:
                logger.warning(
                    "No executor registered for scheduled task %s (id: %s)",
                    task.name,
                    task.id,
                )
                return

            try:
                await executor(task)
            except Exception as e:
                logger.error(
                    "Error executing scheduled task %s (id: %s): %s",
                    task.name,
                    task.id,
                    e,
                    exc_info=True,
                )

        # Run all pending tasks concurrently
        await asyncio.gather(*[_safe_execute(task) for task in tasks_to_run])

        # Cleanup and handle recursion
        for task in tasks_to_run:
            if task.is_recurring and task.interval_ticks > 0:
                # Update target tick for next execution
                task.target_tick = current_tick + task.interval_ticks
                logger.debug(
                    "Rescheduled recurring task %s (id: %s) for tick %d",
                    task.name,
                    task.id,
                    task.target_tick,
                )
            else:
                # Delete task and executor
                self._tasks.pop(task.id, None)
                self._executors.pop(task.id, None)

    def cancel(self, task_id: UUID) -> bool:
        """Cancels a scheduled task by ID.

        Args:
            task_id: The UUID of the scheduled task.

        Returns:
            True if the task was found and cancelled, False otherwise.
        """
        if task_id in self._tasks:
            task = self._tasks.pop(task_id)
            self._executors.pop(task_id, None)
            logger.debug(
                "Cancelled task %s (id: %s)",
                task.name,
                task_id,
            )
            return True
        return False

    def get_all_scheduled_tasks(self) -> list[ScheduledTask]:
        """Retrieves a list of all currently scheduled tasks.

        Returns:
            A list of ScheduledTask instances.
        """
        return list(self._tasks.values())
