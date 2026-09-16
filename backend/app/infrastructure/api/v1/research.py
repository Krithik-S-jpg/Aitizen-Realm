"""Experiment, metrics, timeline, and export endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.application.services.analytics_service import AnalyticsService
from app.domain.models.research import ExperimentStatus
from app.infrastructure.api.dependencies import (
    get_analytics_service,
    get_engine_service,
)

router = APIRouter()


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
