"""Generic entity lifecycle, perception, and private knowledge endpoints."""

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.services.communication_service import CommunicationService
from app.application.services.decision_service import DecisionService
from app.application.services.entity_service import EntityService
from app.application.services.goal_action_service import GoalActionService
from app.application.services.memory_service import MemoryService
from app.application.services.navigation_service import NavigationService
from app.application.services.needs_service import NeedsService
from app.application.services.perception_service import PerceptionService
from app.application.services.society_service import SocietyService
from app.domain.models.entity import CitizenAvatar, Entity, EntityKind
from app.domain.models.memory import EpisodeType
from app.infrastructure.api.dependencies import (
    get_communication_service,
    get_decision_service,
    get_entity_service,
    get_goal_action_service,
    get_memory_service,
    get_navigation_service,
    get_needs_service,
    get_perception_service,
    get_society_service,
)

router = APIRouter()


class CreateEntityRequest(BaseModel):
    """Parameters for a behavior-free generic world entity."""

    kind: EntityKind
    name: str = Field(min_length=1, max_length=80)
    x: int
    y: int
    perception_radius: int = Field(default=6, ge=1, le=32)
    tags: set[str] = Field(default_factory=set)
    avatar_id: CitizenAvatar = CitizenAvatar.SCOUT
    auto_spawn: bool = False


class ObservationRequest(BaseModel):
    """The authoritative tick at which an observation occurs."""

    tick: int = Field(ge=0)


class NeedAmountRequest(BaseModel):
    """Positive amount used by eating, drinking, or resting."""

    amount: float = Field(gt=0.0, le=100.0)
    item_type: str = Field(default="food", min_length=1, max_length=30)


class RouteRequest(BaseModel):
    """Known destination and tick used to create a movement plan."""

    destination_x: int
    destination_y: int
    tick: int = Field(ge=0)


def _entity_payload(entity: Entity) -> dict[str, Any]:
    payload = {
        **entity.model_dump(mode="json"),
        "kind": entity.kind.value.lower(),
    }
    if entity.needs is not None:
        payload["needs"] = {
            **entity.needs.model_dump(),
            "critical": entity.needs.critical,
        }
    return payload


def _movement_payload(plan: Any) -> dict[str, Any]:
    return {
        **plan.model_dump(mode="json"),
        "status": plan.status.value.lower(),
        "remaining_steps": plan.remaining_steps,
    }


def _raise_entity_error(error: Exception) -> NoReturn:
    code = 404 if isinstance(error, LookupError) else 409
    raise HTTPException(status_code=code, detail=str(error)) from error


@router.post("")
def create_entity(
    request: CreateEntityRequest,
    service: EntityService = Depends(get_entity_service),
) -> dict[str, Any]:
    """Creates a generic identity without enabling autonomous behavior."""
    try:
        entity = service.create(
            request.kind,
            request.name,
            request.x,
            request.y,
            request.perception_radius,
            request.tags,
            request.avatar_id,
            auto_spawn=request.auto_spawn,
        )
        return _entity_payload(entity)
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("")
def list_entities(
    service: EntityService = Depends(get_entity_service),
) -> list[dict[str, Any]]:
    """Lists currently active generic entities."""
    try:
        return [_entity_payload(entity) for entity in service.list_active()]
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/admin/overview")
def admin_overview(
    service: EntityService = Depends(get_entity_service),
) -> list[dict[str, object]]:
    """Returns detailed live agent records for the local admin console."""
    try:
        return service.admin_overview()
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}")
def get_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> dict[str, Any]:
    """Returns one entity's public world state."""
    try:
        return _entity_payload(service.get(entity_id))
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.delete("/{entity_id}")
def deactivate_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
) -> dict[str, Any]:
    """Deactivates an entity while preserving its historical knowledge."""
    try:
        return _entity_payload(service.deactivate(entity_id))
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/observe")
def observe_world(
    entity_id: UUID,
    request: ObservationRequest,
    service: PerceptionService = Depends(get_perception_service),
) -> dict[str, Any]:
    """Returns only world state currently visible to an entity."""
    try:
        return service.observe(entity_id, request.tick)
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/knowledge")
def get_entity_knowledge(
    entity_id: UUID,
    service: PerceptionService = Depends(get_perception_service),
) -> dict[str, Any]:
    """Returns the entity's accumulated, potentially stale private knowledge."""
    try:
        return service.knowledge(entity_id).model_dump(mode="json")
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/needs/eat")
def eat(
    entity_id: UUID,
    request: NeedAmountRequest,
    service: NeedsService = Depends(get_needs_service),
) -> dict[str, Any]:
    """Consumes carried food to reduce hunger."""
    try:
        return _entity_payload(
            service.eat(entity_id, request.amount, request.item_type.lower())
        )
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/needs/drink")
def drink(
    entity_id: UUID,
    request: NeedAmountRequest,
    service: NeedsService = Depends(get_needs_service),
) -> dict[str, Any]:
    """Drinks from an adjacent natural water source."""
    try:
        return _entity_payload(
            service.drink_from_environment(entity_id, request.amount)
        )
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/needs/rest")
def rest(
    entity_id: UUID,
    request: NeedAmountRequest,
    service: NeedsService = Depends(get_needs_service),
) -> dict[str, Any]:
    """Restores entity energy."""
    try:
        return _entity_payload(service.rest(entity_id, request.amount))
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/route")
def plan_route(
    entity_id: UUID,
    request: RouteRequest,
    service: NavigationService = Depends(get_navigation_service),
) -> dict[str, Any]:
    """Plans movement through the entity's discovered walkable tiles."""
    try:
        return _movement_payload(
            service.plan(
                entity_id, request.destination_x, request.destination_y, request.tick
            )
        )
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/route")
def get_route(
    entity_id: UUID,
    service: NavigationService = Depends(get_navigation_service),
) -> dict[str, Any]:
    """Returns current backend movement state."""
    try:
        return _movement_payload(service.get_plan(entity_id))
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.delete("/{entity_id}/route")
def cancel_route(
    entity_id: UUID,
    service: NavigationService = Depends(get_navigation_service),
) -> dict[str, Any]:
    """Cancels an unfinished route."""
    try:
        return _movement_payload(service.cancel(entity_id))
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/decisions")
def evaluate_decisions(
    entity_id: UUID,
    service: DecisionService = Depends(get_decision_service),
) -> list[dict[str, Any]]:
    """Returns ranked utility options without changing simulation state."""
    try:
        return [
            {
                **option.model_dump(mode="json"),
                "goal_type": option.goal_type.value.lower(),
            }
            for option in service.evaluate(entity_id)
        ]
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.post("/{entity_id}/decide")
def decide_now(
    entity_id: UUID,
    request: ObservationRequest,
    service: DecisionService = Depends(get_decision_service),
) -> dict[str, Any]:
    """Runs one explainable utility decision immediately."""
    try:
        goal, action = service.decide(entity_id, request.tick)
        return {
            "goal": goal.model_dump(mode="json"),
            "action": action.model_dump(mode="json"),
        }
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/history")
def get_cognition_history(
    entity_id: UUID,
    service: GoalActionService = Depends(get_goal_action_service),
) -> dict[str, Any]:
    """Returns retained goal and action history for debugging and replay."""
    try:
        history = service.history(entity_id)
        return {
            key: [item.model_dump(mode="json") for item in items]
            for key, items in history.items()
        }
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/memories")
def recall_memories(
    entity_id: UUID,
    limit: int = 20,
    episode_type: EpisodeType | None = None,
    near_x: int | None = None,
    near_y: int | None = None,
    radius: int = 5,
    service: MemoryService = Depends(get_memory_service),
) -> list[dict[str, Any]]:
    """Recalls personal episodes by recency, type, and optional location."""
    try:
        return [
            episode.model_dump(mode="json")
            for episode in service.recall(
                entity_id, limit, episode_type, near_x, near_y, radius
            )
        ]
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)


@router.get("/{entity_id}/observation")
def get_entity_observation(
    entity_id: UUID,
    entities: EntityService = Depends(get_entity_service),
    perception: PerceptionService = Depends(get_perception_service),
    lifecycle: GoalActionService = Depends(get_goal_action_service),
    memory: MemoryService = Depends(get_memory_service),
    communication: CommunicationService = Depends(get_communication_service),
    society: SocietyService = Depends(get_society_service),
) -> dict[str, Any]:
    """Returns a versioned, inspect-only citizen observation document."""
    try:
        entity = entities.get(entity_id)
        history = lifecycle.history(entity_id)
        relationships = [
            bond.model_dump(mode="json")
            for bond in society.relationships_for(entity_id)
        ]
        return {
            "schema_version": "1.0",
            "entity": _entity_payload(entity),
            "knowledge": perception.knowledge(entity_id).model_dump(mode="json"),
            "memories": [
                episode.model_dump(mode="json")
                for episode in memory.recall(entity_id, limit=20)
            ],
            "history": {
                key: [item.model_dump(mode="json") for item in items]
                for key, items in history.items()
            },
            "communications": [
                message.model_dump(mode="json")
                for message in communication.history(entity_id)
            ],
            "relationships": relationships,
            "availability": {
                "memory": "available",
                "actions": "available",
                "knowledge": "available",
                "relationships": "available",
                "mood": "not_implemented",
                "age": "not_implemented",
            },
        }
    except (LookupError, ValueError) as error:
        _raise_entity_error(error)
