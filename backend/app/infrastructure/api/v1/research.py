"""Experiment, metrics, timeline, and export endpoints."""

from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.application.services.analytics_service import AnalyticsService
from app.core.config import settings
from app.domain.models.calendar import get_calendar_control
from app.domain.models.engine import EngineState
from app.domain.models.research import ExperimentStatus
from app.infrastructure.api.dependencies import (
    get_analytics_service,
    get_engine_service,
    get_world_service,
)
from app.infrastructure.api.v1.checkpoints import require_admin_token
from app.infrastructure.repositories.supabase_research import SupabaseResearchArchive

router = APIRouter()


def research_archive_store(
    _: None = Depends(require_admin_token),
) -> SupabaseResearchArchive:
    """Creates server-side archive storage after admin authentication."""
    try:
        return SupabaseResearchArchive(
            settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY.get_secret_value()
        )
    except ValueError as error:
        raise HTTPException(503, str(error)) from None


class ExperimentRequest(BaseModel):
    """User-defined reproducible experiment settings."""

    name: str = Field(min_length=1, max_length=120)
    seed: int = Field(ge=0, le=2_147_483_647)
    parameters: dict[str, object] = Field(default_factory=dict)


@router.get("/metrics")
def metrics(
    limit: int = Query(default=500, ge=1, le=10_000),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[dict[str, Any]]:
    """Returns recent aggregate simulation measurements."""
    return [snapshot.model_dump(mode="json") for snapshot in service.history(limit)]


@router.get("/events")
def world_events(
    after_sequence: int = Query(default=-1, ge=-1),
    limit: int = Query(default=100, ge=1, le=500),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[dict[str, Any]]:
    """Returns meaningful world changes for notifications and the journal."""
    return [
        event.model_dump(mode="json")
        for event in service.events(after_sequence=after_sequence, limit=limit)
    ]


@router.get("/experiments")
def experiments(
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[dict[str, Any]]:
    """Lists configured experiments."""
    return [item.model_dump(mode="json") for item in service.experiments()]


@router.post("/experiments")
def create_experiment(
    request: ExperimentRequest,
    service: AnalyticsService = Depends(get_analytics_service),
    engine: Any = Depends(get_engine_service),
) -> dict[str, Any]:
    """Creates a draft experiment at the current simulation tick."""
    experiment = service.create_experiment(
        request.name,
        request.seed,
        request.parameters,
        engine.get_current_tick().value,
    )
    return experiment.model_dump(mode="json")


@router.post("/experiments/{experiment_id}/{status}")
def update_experiment(
    experiment_id: UUID,
    status: ExperimentStatus,
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, Any]:
    """Updates an experiment lifecycle state."""
    try:
        return service.set_status(experiment_id, status).model_dump(mode="json")
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/export")
def export_research(
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, object]:
    """Exports metrics, experiments, and historical events as JSON."""
    try:
        return service.export()
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/archive", status_code=201)
async def archive_research(
    service: AnalyticsService = Depends(get_analytics_service),
    engine: Any = Depends(get_engine_service),
    store: SupabaseResearchArchive = Depends(research_archive_store),
) -> dict[str, object]:
    """Atomically archives real run metadata, experiments, metrics, and events."""
    if engine.get_simulation_state() == EngineState.RUNNING:
        raise HTTPException(409, "Pause the simulation before archiving research")
    world = get_world_service().get_world()
    if world is None:
        raise HTTPException(409, "Create a world before archiving research")
    run_id = uuid4()
    archive = {
        "id": str(run_id),
        "world_seed": world.seed,
        "world_width": world.width,
        "world_height": world.height,
        "current_tick": engine.get_current_tick().value,
        "tick_rate": engine.get_tick_rate(),
        "calendar": get_calendar_control().model_dump(mode="json"),
        "experiments": [item.model_dump(mode="json") for item in service.experiments()],
        "metrics": [
            item.model_dump(mode="json")
            for item in service.history(service.MAX_HISTORY)
        ],
        "events": [item.model_dump(mode="json") for item in service.all_events()],
    }
    try:
        stored_id = await store.save(archive)
    except httpx.HTTPError:
        raise HTTPException(502, "Research archive storage request failed") from None
    return {
        "run_id": stored_id,
        "experiments": len(archive["experiments"]),
        "metrics": len(archive["metrics"]),
        "events": len(archive["events"]),
    }
