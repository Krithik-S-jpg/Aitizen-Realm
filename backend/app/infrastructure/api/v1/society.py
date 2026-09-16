"""Society observation endpoints for groups, professions, and relationships."""

from typing import Any

from fastapi import APIRouter, Depends

from app.application.services.society_service import SocietyService
from app.infrastructure.api.dependencies import get_society_service

router = APIRouter()


@router.get("/overview")
def society_overview(
    service: SocietyService = Depends(get_society_service),
) -> dict[str, Any]:
    """Returns the active social graph and emergent groups."""
    return service.overview()
