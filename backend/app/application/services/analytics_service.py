"""Research metrics, experiment configuration, and compact data export."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.research import (
    Experiment,
    ExperimentStatus,
    MetricsSnapshot,
)
from app.domain.models.world import World


class AnalyticsService:
    """Captures deterministic aggregate metrics without influencing agents."""

    MAX_HISTORY = 10_000

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes analytics against the authoritative world."""
        self._repository = repository
        self._history: list[MetricsSnapshot] = []
        self._experiments: dict[str, Experiment] = {}

    def capture(self, tick: int) -> MetricsSnapshot | None:
        """Records one aggregate snapshot for a completed tick."""
        world = self._repository.get()
        if world is None:
            return None
        living = [
            entity
            for entity in world.entities.values()
            if entity.active and entity.needs is not None
        ]
        health = [entity.needs.health for entity in living if entity.needs is not None]
        hunger = [entity.needs.hunger for entity in living if entity.needs is not None]
        snapshot = MetricsSnapshot(
            tick=tick,
            population=len(living),
            average_health=round(sum(health) / len(health), 2) if health else 0.0,
            average_hunger=round(sum(hunger) / len(hunger), 2) if hunger else 0.0,
            resources_available=round(
                sum(resource.quantity for resource in world.resources.values()), 2
            ),
            structures=len(world.structures),
            completed_structures=sum(
                structure.completed for structure in world.structures.values()
            ),
            groups=len(world.groups),
            communications=len(world.messages),
        )
        self._history.append(snapshot)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY :]
        return snapshot

    def history(self, limit: int = 500) -> list[MetricsSnapshot]:
        """Returns recent metrics in chronological order."""
        return self._history[-max(1, min(limit, self.MAX_HISTORY)) :]

    def create_experiment(
        self,
        name: str,
        seed: int,
        parameters: dict[str, object],
        current_tick: int,
    ) -> Experiment:
        """Registers a reproducible experiment configuration."""
        experiment = Experiment(
            name=name,
            seed=seed,
            parameters=parameters,
            created_at_tick=current_tick,
        )
        self._experiments[str(experiment.id)] = experiment
        return experiment

    def set_status(self, experiment_id: UUID, status: ExperimentStatus) -> Experiment:
        """Transitions an existing experiment state."""
        experiment = self._experiments.get(str(experiment_id))
        if experiment is None:
            raise LookupError("Experiment does not exist.")
        experiment.status = status
        return experiment

    def experiments(self) -> list[Experiment]:
        """Returns experiments in stable creation order."""
        return list(self._experiments.values())

    def export(self) -> dict[str, object]:
        """Produces a compact JSON-compatible research bundle."""
        world = self._require_world()
        return {
            "world": {
                "seed": world.seed,
                "width": world.width,
                "height": world.height,
                "chunks": len(world.chunks),
            },
            "experiments": [
                item.model_dump(mode="json") for item in self.experiments()
            ],
            "metrics": [item.model_dump(mode="json") for item in self._history],
            "timeline": [
                {
                    "tick": episode.tick,
                    "entity_id": str(episode.entity_id),
                    "type": episode.episode_type.value.lower(),
                    "summary": episode.summary,
                }
                for episodes in world.episodes.values()
                for episode in episodes
            ],
        }

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
