"""Research metrics, experiment configuration, and compact data export."""

from uuid import UUID

from app.application.services.settlement_observation import settlement_reports
from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.calendar import calendar_at_tick
from app.domain.models.cognition import ActionType, TaskStatus
from app.domain.models.entity import EntityKind
from app.domain.models.research import (
    EventSeverity,
    Experiment,
    ExperimentStatus,
    MetricsSnapshot,
    WorldEvent,
)
from app.domain.models.world import World


class AnalyticsService:
    """Captures deterministic aggregate metrics without influencing agents."""

    MAX_HISTORY = 10_000
    MAX_EVENTS = 2_000

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes analytics against the authoritative world."""
        self._repository = repository
        self._history: list[MetricsSnapshot] = []
        self._experiments: dict[str, Experiment] = {}
        self._events: list[WorldEvent] = []
        self._event_keys: set[str] = set()
        self._event_key_order: list[str] = []
        self._next_event_sequence = 0
        self._last_weather: str | None = None

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
        wildlife_by_species: dict[str, int] = {}
        births = 0
        deaths = 0
        for entity in world.entities.values():
            if entity.kind.value == "ANIMAL":
                species = str(entity.metadata.get("species", "unknown"))
                if entity.active:
                    wildlife_by_species[species] = (
                        wildlife_by_species.get(species, 0) + 1
                    )
                if int(entity.metadata.get("birth_tick", -1)) == tick:
                    births += 1
                if int(entity.metadata.get("death_tick", -1)) == tick:
                    deaths += 1
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
            wildlife_by_species=wildlife_by_species,
            births=births,
            deaths=deaths,
        )
        self._history.append(snapshot)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY :]
        self._capture_events(world, tick)
        return snapshot

    def events(self, after_sequence: int = -1, limit: int = 100) -> list[WorldEvent]:
        """Returns recent meaningful changes in chronological order."""
        matches = [event for event in self._events if event.sequence > after_sequence]
        return matches[: max(1, min(limit, 500))]

    def all_events(self) -> list[WorldEvent]:
        """Returns the complete bounded event buffer for explicit persistence."""
        return list(self._events)

    def _capture_events(self, world: World, tick: int) -> None:
        """Derives readable events from authoritative state transitions."""
        calendar = calendar_at_tick(tick)
        weather = calendar.weather.value
        if self._last_weather is not None and weather != self._last_weather:
            self._record(
                f"weather:{tick}:{weather}",
                WorldEvent(
                    tick=tick,
                    event_type="weather",
                    severity=EventSeverity.WARNING
                    if weather != "CLEAR"
                    else EventSeverity.INFO,
                    title="Weather changed",
                    summary=f"{weather.title()} moved into the observed region.",
                    data={"weather": weather, "intensity": calendar.weather_intensity},
                ),
            )
        self._last_weather = weather
        for entity in world.entities.values():
            entity_id = str(entity.id)
            if int(entity.metadata.get("birth_tick", -1)) == tick:
                species = str(entity.metadata.get("species", "citizen")).title()
                self._record(
                    f"birth:{entity_id}",
                    WorldEvent(
                        tick=tick,
                        event_type="birth",
                        severity=EventSeverity.SUCCESS,
                        title=f"New {species}",
                        summary=f"A {species.lower()} was born into the living world.",
                        entity_id=entity.id,
                        x=entity.x,
                        y=entity.y,
                    ),
                )
            if int(entity.metadata.get("death_tick", -1)) == tick:
                species = str(entity.metadata.get("species", entity.name)).title()
                hunted = bool(entity.metadata.get("killed_by"))
                cause = str(
                    entity.metadata.get("death_cause", "unknown causes")
                ).replace("_", " ")
                self._record(
                    f"death:{entity_id}",
                    WorldEvent(
                        tick=tick,
                        event_type="hunt" if hunted else "death",
                        severity=EventSeverity.DANGER,
                        title="Predator kill" if hunted else f"{species} died",
                        summary=(
                            f"A predator caught a {species.lower()}."
                            if hunted
                            else f"{species} died from {cause}."
                        ),
                        entity_id=entity.id,
                        x=entity.x,
                        y=entity.y,
                        data={
                            "cause": cause,
                            "killed_by": entity.metadata.get("killed_by"),
                        },
                    ),
                )
            if int(entity.metadata.get("sleeping_since_tick", -1)) == tick:
                self._record(
                    f"sleep:{entity_id}:{tick}",
                    WorldEvent(
                        tick=tick,
                        event_type="sleep",
                        title=f"{entity.name} went to sleep",
                        summary=(
                            "The citizen suspended work to recover through the night."
                        ),
                        entity_id=entity.id,
                        x=entity.x,
                        y=entity.y,
                    ),
                )
            if int(entity.metadata.get("woke_at_tick", -1)) == tick:
                self._record(
                    f"wake:{entity_id}:{tick}",
                    WorldEvent(
                        tick=tick,
                        event_type="wake",
                        title=f"{entity.name} woke up",
                        summary="The citizen resumed life as daylight returned.",
                        entity_id=entity.id,
                        x=entity.x,
                        y=entity.y,
                    ),
                )
        for structure in world.structures.values():
            if structure.completed:
                self._record(
                    f"structure:{structure.id}",
                    WorldEvent(
                        tick=tick,
                        event_type="construction",
                        severity=EventSeverity.SUCCESS,
                        title=f"{structure.structure_type.value.title()} completed",
                        summary=(
                            "A new structure is operational and can affect future "
                            "decisions."
                        ),
                        x=structure.x,
                        y=structure.y,
                        data={"structure_id": str(structure.id)},
                    ),
                )
        for group in world.groups.values():
            if group.formed_at_tick == tick:
                self._record(
                    f"group:{group.id}",
                    WorldEvent(
                        tick=tick,
                        event_type="society",
                        severity=EventSeverity.SUCCESS,
                        title="New social group",
                        summary=(
                            f"{group.name} formed with {len(group.member_ids)} "
                            "founding members."
                        ),
                        x=group.home_x,
                        y=group.home_y,
                        data={"group_id": str(group.id)},
                    ),
                )
        interesting_actions = {
            ActionType.CHOP: ("tree_felled", "Tree felled"),
            ActionType.CRAFT: ("crafted", "Item crafted"),
            ActionType.PLUCK: ("harvest", "Food harvested"),
        }
        for action in world.actions.values():
            if (
                action.status != TaskStatus.COMPLETED
                or action.completed_at_tick != tick
                or action.action_type not in interesting_actions
            ):
                continue
            actor = world.entities.get(str(action.entity_id))
            event_type, title = interesting_actions[action.action_type]
            self._record(
                f"action:{action.id}",
                WorldEvent(
                    tick=tick,
                    event_type=event_type,
                    severity=EventSeverity.SUCCESS,
                    title=title,
                    summary=(
                        f"{actor.name if actor else 'A citizen'} completed "
                        f"{action.action_type.value.lower()} work."
                    ),
                    entity_id=action.entity_id,
                    x=actor.x if actor else None,
                    y=actor.y if actor else None,
                    data=action.result,
                ),
            )

    def _record(self, key: str, event: WorldEvent) -> None:
        if key in self._event_keys:
            return
        self._event_keys.add(key)
        self._event_key_order.append(key)
        event.sequence = self._next_event_sequence
        self._next_event_sequence += 1
        self._events.append(event)
        if len(self._events) > self.MAX_EVENTS:
            overflow = len(self._events) - self.MAX_EVENTS
            self._events = self._events[-self.MAX_EVENTS :]
            for removed_key in self._event_key_order[:overflow]:
                self._event_keys.discard(removed_key)
            self._event_key_order = self._event_key_order[overflow:]

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
            "groups": [
                group.model_dump(mode="json") for group in world.groups.values()
            ],
            "settlements": settlement_reports(world),
            "households": [
                household.model_dump(mode="json")
                for household in world.households.values()
            ],
            "settlement_jobs": [
                job.model_dump(mode="json")
                for job in world.settlement_jobs.values()
                if job.status != "completed"
            ],
            "wildlife": [
                animal.model_dump(mode="json")
                for animal in world.entities.values()
                if animal.kind == EntityKind.ANIMAL and animal.active
            ],
            "buildings": [
                {
                    **site.model_dump(mode="json"),
                    "completed": site.completed,
                    "funded": site.funded,
                    "missing_materials": site.missing_materials,
                    "progress_ratio": min(1.0, site.progress / site.work_required),
                }
                for site in world.structures.values()
            ],
            "economy": {
                "inventories": len(world.inventories),
                "stock": self._inventory_totals(world),
                "structures": len(world.structures),
                "completed_structures": sum(
                    site.completed for site in world.structures.values()
                ),
            },
            "metrics": [item.model_dump(mode="json") for item in self._history],
            "timeline": sorted(
                [
                    {
                        "tick": episode.tick,
                        "entity_id": str(episode.entity_id),
                        "type": episode.episode_type.value.lower(),
                        "summary": episode.summary,
                    }
                    for episodes in world.episodes.values()
                    for episode in episodes
                ]
                + [
                    {
                        "tick": event.tick,
                        "entity_id": str(event.entity_id) if event.entity_id else None,
                        "type": event.event_type,
                        "summary": event.summary,
                        "severity": event.severity.value.lower(),
                        "x": event.x,
                        "y": event.y,
                    }
                    for event in self._events
                ],
                key=lambda item: int(str(item["tick"])),
            ),
        }

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world

    @staticmethod
    def _inventory_totals(world: World) -> dict[str, float]:
        """Report stored inventory materials without inventing market prices."""
        totals: dict[str, float] = {}
        for inventory in [
            *world.inventories.values(),
            *(site.stockpile for site in world.structures.values()),
        ]:
            for material, quantity in inventory.items.items():
                totals[material] = totals.get(material, 0.0) + quantity
        return totals
