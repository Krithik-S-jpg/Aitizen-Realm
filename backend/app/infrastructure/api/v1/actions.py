"""Resource gathering and construction endpoints for simulation actors."""

from typing import Any, Literal, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.services.construction_service import ConstructionService
from app.application.services.resource_service import ResourceService
from app.domain.models.structure import StructureType
from app.infrastructure.api.dependencies import (
    get_construction_service,
    get_resource_service,
)

router = APIRouter()


class ReservationRequest(BaseModel):
    """Request to claim a resource for a bounded number of ticks."""

    actor_id: str = Field(min_length=1)
    current_tick: int = Field(ge=0)
    duration_ticks: int = Field(default=20, gt=0, le=1000)


class ActorRequest(BaseModel):
    """Request identifying the actor performing an action."""

    actor_id: str = Field(min_length=1)


class GatherRequest(ActorRequest):
    """Request to transfer resource quantity into carried inventory."""

    amount: float = Field(gt=0.0)
    current_tick: int = Field(ge=0)


class PlaceStructureRequest(ActorRequest):
    """Request to consume a blueprint recipe and place a site."""

    structure_type: StructureType
    x: int
    y: int


class WorkRequest(ActorRequest):
    """Request to contribute construction work."""

    amount: float = Field(gt=0.0)


class StorageTransferRequest(ActorRequest):
    """A local, capacity-limited material transfer."""

    item: str = Field(min_length=1)
    amount: float = Field(gt=0.0, allow_inf_nan=False)
    direction: Literal["deposit", "withdraw"] = "deposit"


@router.post("/structures/{structure_id}/transfer")
def transfer_storage(
    structure_id: UUID,
    request: StorageTransferRequest,
    service: ConstructionService = Depends(get_construction_service),
) -> dict[str, Any]:
    """Deposits or withdraws carried material at a completed storage building."""
    try:
        amount = service.transfer_storage(
            structure_id,
            request.actor_id,
            request.item,
            request.amount,
            request.direction == "withdraw",
        )
        return {
            "transferred": amount,
            "item": request.item,
            "direction": request.direction,
        }
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


def _resource_payload(resource: Any) -> dict[str, Any]:
    return {
        "id": resource.id,
        "type": resource.resource_type.value.lower(),
        "x": resource.x,
        "y": resource.y,
        "quantity": resource.quantity,
        "capacity": resource.capacity,
        "depleted": resource.depleted,
        "reserved_by": resource.reserved_by,
        "reservation_expires_at": resource.reservation_expires_at,
        "variant": resource.variant,
        "produce_type": resource.produce_type,
        "produce_quantity": resource.produce_quantity,
        "produce_capacity": resource.produce_capacity,
    }


def _structure_payload(structure: Any) -> dict[str, Any]:
    return {
        **structure.model_dump(mode="json"),
        "structure_type": structure.structure_type.value.lower(),
        "completed": structure.completed,
        "funded": structure.funded,
        "missing_materials": structure.missing_materials,
        "progress_ratio": structure.progress / structure.work_required,
    }


def _inventory_payload(inventory: Any) -> dict[str, Any]:
    return {**inventory.model_dump(), "carried": inventory.carried}


def _raise_action_error(error: Exception) -> NoReturn:
    status_code = 404 if isinstance(error, LookupError) else 409
    raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.post("/resources/{resource_id}/reserve")
def reserve_resource(
    resource_id: UUID,
    request: ReservationRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Reserves one resource for an actor."""
    try:
        resource = service.reserve(
            resource_id, request.actor_id, request.current_tick, request.duration_ticks
        )
        return _resource_payload(resource)
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/resources/{resource_id}/release")
def release_resource(
    resource_id: UUID,
    request: ActorRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Releases one actor-owned resource reservation."""
    try:
        return _resource_payload(service.release(resource_id, request.actor_id))
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/resources/{resource_id}/gather")
def gather_resource(
    resource_id: UUID,
    request: GatherRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Gathers a reserved resource into actor inventory."""
    try:
        resource, inventory, gathered = service.gather(
            resource_id, request.actor_id, request.amount, request.current_tick
        )
        return {
            "gathered": gathered,
            "resource": _resource_payload(resource),
            "inventory": _inventory_payload(inventory),
        }
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/resources/{resource_id}/chop")
def chop_tree(
    resource_id: UUID,
    request: GatherRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Fells a reachable tree into ground timber; collection is a separate action."""
    try:
        resource, inventory, chopped = service.chop(
            resource_id, request.actor_id, request.amount, request.current_tick
        )
        return {
            "chopped": chopped,
            "resource": _resource_payload(resource),
            "inventory": _inventory_payload(inventory),
        }
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/resources/{resource_id}/pluck")
def pluck_produce(
    resource_id: UUID,
    request: GatherRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Plucks ripe produce without destroying its parent resource."""
    try:
        resource, inventory, plucked = service.pluck(
            resource_id, request.actor_id, request.amount
        )
        return {
            "plucked": plucked,
            "item_type": resource.produce_type,
            "resource": _resource_payload(resource),
            "inventory": _inventory_payload(inventory),
        }
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.get("/actors/{actor_id}/inventory")
def get_inventory(
    actor_id: str, service: ResourceService = Depends(get_resource_service)
) -> dict[str, Any]:
    """Returns one actor's carried inventory."""
    return _inventory_payload(service.inventory_for(actor_id))


@router.get("/blueprints")
def get_blueprints(
    service: ConstructionService = Depends(get_construction_service),
) -> dict[str, dict[str, object]]:
    """Returns construction recipes and work requirements."""
    blueprints = service.blueprints()
    for item_type, materials in ResourceService.CRAFTING_RECIPES.items():
        blueprints[item_type] = {
            "materials": materials,
            "work_required": 3.0,
            "category": "craft",
        }
    return blueprints


@router.post("/craft/{item_type}")
def craft_item(
    item_type: str,
    request: ActorRequest,
    service: ResourceService = Depends(get_resource_service),
) -> dict[str, Any]:
    """Crafts a carried tool or equipment item from raw materials."""
    try:
        return {
            "item_type": item_type,
            "inventory": _inventory_payload(
                service.craft(request.actor_id, item_type.lower())
            ),
        }
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/structures")
def place_structure(
    request: PlaceStructureRequest,
    service: ConstructionService = Depends(get_construction_service),
) -> dict[str, Any]:
    """Places a paid, unfinished construction site."""
    try:
        return _structure_payload(
            service.place(
                request.actor_id, request.structure_type, request.x, request.y
            )
        )
    except (LookupError, ValueError) as error:
        _raise_action_error(error)


@router.post("/structures/{structure_id}/work")
def work_on_structure(
    structure_id: UUID,
    request: WorkRequest,
    service: ConstructionService = Depends(get_construction_service),
) -> dict[str, Any]:
    """Contributes work to a construction site."""
    try:
        return _structure_payload(
            service.apply_work(structure_id, request.actor_id, request.amount)
        )
    except (LookupError, ValueError) as error:
        _raise_action_error(error)
