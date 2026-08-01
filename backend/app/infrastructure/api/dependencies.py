"""Dependency injection providers for FastAPI controllers.

Maintains and provides singleton instances of core simulation components.
"""

from app.application.services.engine_service import EngineService
from app.core.config import settings
from app.domain.interfaces.engine import ISimulationEngine
from app.domain.interfaces.event_bus import IEventBus
from app.domain.interfaces.scheduler import IScheduler
from app.infrastructure.engine.loop_engine import LoopEngine
from app.infrastructure.event_bus.memory_bus import InMemoryEventBus
from app.infrastructure.scheduler.memory_scheduler import MemoryScheduler

# Singletons initialization
_event_bus = InMemoryEventBus()
_scheduler = MemoryScheduler()
_engine = LoopEngine(
    event_bus=_event_bus,
    scheduler=_scheduler,
    ticks_per_second=settings.DEFAULT_TICK_RATE,
)
_engine_service = EngineService(engine=_engine)


def get_event_bus() -> IEventBus:
    """Returns the singleton IEventBus instance."""
    return _event_bus


def get_scheduler() -> IScheduler:
    """Returns the singleton IScheduler instance."""
    return _scheduler


def get_engine() -> ISimulationEngine:
    """Returns the singleton ISimulationEngine instance."""
    return _engine


def get_engine_service() -> EngineService:
    """Returns the singleton EngineService instance."""
    return _engine_service
