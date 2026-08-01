"""Tests for the MemoryScheduler implementation."""

import pytest

from app.domain.interfaces.scheduler import IScheduler
from app.domain.models.engine import ScheduledTask


@pytest.mark.asyncio
async def test_scheduler_one_time_task(scheduler: IScheduler) -> None:
    """Tests that a single non-recurring task is executed and removed."""
    executed_tasks: list[ScheduledTask] = []

    async def mock_executor(task: ScheduledTask) -> None:
        executed_tasks.append(task)

    # Schedule for tick 5
    task = scheduler.schedule(
        name="one_time",
        target_tick=5,
        executor=mock_executor,
        payload={"arg": "value"},
    )

    # Tick 4: should not execute
    await scheduler.process_tick(4)
    assert len(executed_tasks) == 0
    assert len(scheduler.get_all_scheduled_tasks()) == 1

    # Tick 5: should execute
    await scheduler.process_tick(5)
    assert len(executed_tasks) == 1
    assert executed_tasks[0].id == task.id
    assert executed_tasks[0].payload == {"arg": "value"}
    # Should be removed from pending pool
    assert len(scheduler.get_all_scheduled_tasks()) == 0


@pytest.mark.asyncio
async def test_scheduler_recurring_task(scheduler: IScheduler) -> None:
    """Tests that a recurring task executes and reschedules itself."""
    executions: list[int] = []

    async def mock_executor(task: ScheduledTask) -> None:
        executions.append(task.target_tick)

    # Schedule a task at tick 3, repeating every 4 ticks
    scheduler.schedule(
        name="recurring",
        target_tick=3,
        executor=mock_executor,
        is_recurring=True,
        interval_ticks=4,
    )

    # Step to tick 2: nothing
    await scheduler.process_tick(2)
    assert len(executions) == 0

    # Step to tick 3: executes first time
    await scheduler.process_tick(3)
    assert executions == [3]
    # Check that it rescheduled for tick 7
    all_tasks = scheduler.get_all_scheduled_tasks()
    assert len(all_tasks) == 1
    assert all_tasks[0].target_tick == 7

    # Step to tick 6: nothing new
    await scheduler.process_tick(6)
    assert executions == [3]

    # Step to tick 7: executes second time
    await scheduler.process_tick(7)
    assert executions == [3, 7]
    assert scheduler.get_all_scheduled_tasks()[0].target_tick == 11


@pytest.mark.asyncio
async def test_scheduler_cancel_task(scheduler: IScheduler) -> None:
    """Tests that a scheduled task can be cancelled and will not run."""
    executions: list[str] = []

    async def mock_executor(task: ScheduledTask) -> None:
        executions.append(task.name)

    task = scheduler.schedule(
        name="cancel_me",
        target_tick=5,
        executor=mock_executor,
    )

    assert len(scheduler.get_all_scheduled_tasks()) == 1

    # Cancel the task
    cancelled = scheduler.cancel(task.id)
    assert cancelled
    assert len(scheduler.get_all_scheduled_tasks()) == 0

    # Step to tick 5: should not run
    await scheduler.process_tick(5)
    assert len(executions) == 0

    # Try to cancel again
    recancelled = scheduler.cancel(task.id)
    assert not recancelled
