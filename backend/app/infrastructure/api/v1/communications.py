"""Local speech and selective knowledge-sharing endpoints."""

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.services.communication_service import CommunicationService
from app.infrastructure.api.dependencies import get_communication_service

router = APIRouter()


class SendMessageRequest(BaseModel):
    """A local message with an optional bounded set of knowledge keys."""

    sender_id: UUID
    recipient_id: UUID
    tick: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=500)
    shared_records: dict[str, list[str]] = Field(default_factory=dict)


def _raise_communication_error(error: Exception) -> NoReturn:
    code = 404 if isinstance(error, LookupError) else 409
    raise HTTPException(status_code=code, detail=str(error)) from error


@router.post("")
def send_message(
    request: SendMessageRequest,
    service: CommunicationService = Depends(get_communication_service),
) -> dict[str, Any]:
    """Sends a local message and explicitly selected knowledge."""
    try:
        return service.send(
            request.sender_id,
            request.recipient_id,
            request.content,
            request.tick,
            request.shared_records,
        ).model_dump(mode="json")
    except (LookupError, ValueError) as error:
        _raise_communication_error(error)


@router.get("/{entity_id}")
def communication_history(
    entity_id: UUID,
    service: CommunicationService = Depends(get_communication_service),
) -> list[dict[str, Any]]:
    """Returns messages sent or received by one entity."""
    try:
        return [item.model_dump(mode="json") for item in service.history(entity_id)]
    except (LookupError, ValueError) as error:
        _raise_communication_error(error)
