"""Pytest configurations and fixtures for Aitizen Realm tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.domain.interfaces.event_bus import IEventBus
from app.domain.interfaces.scheduler import IScheduler
from app.infrastructure.engine.loop_engine import LoopEngine
from app.infrastructure.event_bus.memory_bus import InMemoryEventBus
from app.infrastructure.scheduler.memory_scheduler import MemoryScheduler
from app.main import app


@pytest.fixture
def event_bus() -> IEventBus:
    """Fixture for a fresh InMemoryEventBus instance."""
    return InMemoryEventBus()


@pytest.fixture
def scheduler() -> IScheduler:
    """Fixture for a fresh MemoryScheduler instance."""
    return MemoryScheduler()


@pytest.fixture
def engine(event_bus: IEventBus, scheduler: IScheduler) -> LoopEngine:
    """Fixture for a fresh LoopEngine instance."""
    # We set ticks_per_second to 10.0 so that async timed loops run faster in tests
    return LoopEngine(event_bus=event_bus, scheduler=scheduler, ticks_per_second=10.0)


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Fixture for FastAPI TestClient."""
    with TestClient(app) as client:
        yield client
