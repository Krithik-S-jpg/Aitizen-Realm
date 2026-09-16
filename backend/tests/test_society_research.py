"""Society formation and reproducible research analytics tests."""

from app.application.services.analytics_service import AnalyticsService
from app.application.services.entity_service import EntityService
from app.application.services.society_service import SocietyService
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import EntityKind
from app.domain.models.research import ExperimentStatus
from app.domain.models.society import Profession
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def _systems() -> tuple[EntityService, SocietyService, AnalyticsService]:
    repository = InMemoryWorldRepository()
    world = WorldGenerator.generate_flat_world(24, 24)
    world.seed = 42
    repository.save(world)
    return (
        EntityService(repository),
        SocietyService(repository),
        AnalyticsService(repository),
    )


def test_nearby_agents_form_a_group_and_specialize() -> None:
    """Local agents organize and practical experience determines profession."""
    entities, society, _ = _systems()
    founder = entities.create(EntityKind.AGENT, "Founder", 8, 8)
    builder = entities.create(EntityKind.AGENT, "Builder", 10, 8)
    SocietyService.add_skill_experience(builder, "building", 15.0)

    society.advance_all(12)

    overview = society.overview()
    assert len(overview["groups"]) == 1
    assert founder.group_id is not None
    assert founder.group_id == builder.group_id
    assert builder.profession == Profession.BUILDER


def test_interactions_create_bounded_social_trust() -> None:
    """Repeated encounters build a queryable directional relationship."""
    entities, society, _ = _systems()
    source = entities.create(EntityKind.AGENT, "Speaker", 4, 4)
    target = entities.create(EntityKind.AGENT, "Listener", 5, 4)

    first = society.register_interaction(source.id, target.id, 2)
    second = society.register_interaction(source.id, target.id, 3, positive=False)

    assert first is second
    assert second.interactions == 2
    assert second.last_interaction_tick == 3
    assert -1.0 <= second.trust <= 1.0


def test_metrics_experiments_and_export_share_one_timeline() -> None:
    """Experiment metadata and aggregate observations export together."""
    entities, society, analytics = _systems()
    entities.create(EntityKind.AGENT, "Observer", 6, 6)
    entities.create(EntityKind.AGENT, "Partner", 7, 6)
    society.advance_all(1)

    snapshot = analytics.capture(1)
    experiment = analytics.create_experiment(
        "Two-agent survival", 42, {"weather": "RAIN", "speed": 1.0}, 1
    )
    analytics.set_status(experiment.id, ExperimentStatus.ACTIVE)
    exported = analytics.export()

    assert snapshot is not None
    assert snapshot.population == 2
    assert snapshot.groups == 1
    assert exported["world"]["seed"] == 42
    assert exported["experiments"][0]["status"] == "ACTIVE"
    assert exported["metrics"][0]["tick"] == 1
