"""Dependency injection providers for FastAPI controllers.

Maintains and provides singleton instances of core simulation components.
"""

from app.application.services.analytics_service import AnalyticsService
from app.application.services.animal_service import AnimalService
from app.application.services.communication_service import CommunicationService
from app.application.services.construction_service import ConstructionService
from app.application.services.decision_service import DecisionService
from app.application.services.engine_service import EngineService
from app.application.services.entity_service import EntityService
from app.application.services.goal_action_service import GoalActionService
from app.application.services.memory_service import MemoryService
from app.application.services.navigation_service import NavigationService
from app.application.services.needs_service import NeedsService
from app.application.services.perception_service import PerceptionService
from app.application.services.resource_service import ResourceService
from app.application.services.society_service import SocietyService
from app.application.services.world_service import WorldService
from app.core.config import settings
from app.domain.interfaces.engine import ISimulationEngine
from app.domain.interfaces.event_bus import IEventBus
from app.domain.interfaces.scheduler import IScheduler
from app.domain.models.engine import Event
from app.infrastructure.engine.loop_engine import LoopEngine
from app.infrastructure.event_bus.memory_bus import InMemoryEventBus
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository
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

_world_repository = InMemoryWorldRepository()
_world_service = WorldService(repository=_world_repository)
_resource_service = ResourceService(repository=_world_repository)
_construction_service = ConstructionService(repository=_world_repository)
_entity_service = EntityService(repository=_world_repository)
_perception_service = PerceptionService(repository=_world_repository)
_needs_service = NeedsService(repository=_world_repository)
_navigation_service = NavigationService(repository=_world_repository)
_animal_service = AnimalService(repository=_world_repository)
_goal_action_service = GoalActionService(repository=_world_repository)
_memory_service = MemoryService(repository=_world_repository)
_society_service = SocietyService(repository=_world_repository)
_analytics_service = AnalyticsService(repository=_world_repository)
_communication_service = CommunicationService(
    repository=_world_repository,
    memory_service=_memory_service,
    society_service=_society_service,
)
_decision_service = DecisionService(
    repository=_world_repository,
    perception=_perception_service,
    needs=_needs_service,
    navigation=_navigation_service,
    resources=_resource_service,
    lifecycle=_goal_action_service,
    construction=_construction_service,
)


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


def get_world_service() -> WorldService:
    """Returns the singleton WorldService instance."""
    return _world_service


def get_resource_service() -> ResourceService:
    """Returns the singleton resource action service."""
    return _resource_service


def get_construction_service() -> ConstructionService:
    """Returns the singleton construction service."""
    return _construction_service


def get_entity_service() -> EntityService:
    """Returns the singleton generic entity service."""
    return _entity_service


def get_perception_service() -> PerceptionService:
    """Returns the singleton limited-perception service."""
    return _perception_service


def get_needs_service() -> NeedsService:
    """Returns the singleton living-needs service."""
    return _needs_service


def get_navigation_service() -> NavigationService:
    """Returns the singleton backend navigation service."""
    return _navigation_service


def get_goal_action_service() -> GoalActionService:
    """Returns the singleton goal and action lifecycle service."""
    return _goal_action_service


def get_decision_service() -> DecisionService:
    """Returns the singleton utility decision service."""
    return _decision_service


def get_memory_service() -> MemoryService:
    """Returns the singleton episodic and spatial memory service."""
    return _memory_service


def get_communication_service() -> CommunicationService:
    """Returns the singleton local communication service."""
    return _communication_service


def get_society_service() -> SocietyService:
    """Returns the singleton emergent-society service."""
    return _society_service


def get_analytics_service() -> AnalyticsService:
    """Returns the singleton research and metrics service."""
    return _analytics_service


async def advance_world_resources(event: Event) -> None:
    """Advances backend-owned resource growth after each completed tick."""
    _world_service.advance_resources(event.tick)


async def advance_world_entities(event: Event) -> None:
    """Advances authoritative movement before applying tick needs."""
    _navigation_service.advance_all(event.tick)
    _needs_service.advance_all(event.tick)
    _animal_service.advance_all(event.tick)
    _decision_service.advance_all(event.tick)
    _memory_service.decay_all(event.tick)
    _society_service.advance_all(event.tick)


async def capture_world_metrics(event: Event) -> None:
    """Records one non-invasive research snapshot after a completed tick."""
    _analytics_service.capture(event.tick)
