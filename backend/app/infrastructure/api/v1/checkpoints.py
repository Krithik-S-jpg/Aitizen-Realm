"""Authenticated explicit backups of a paused authoritative simulation."""

import secrets
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.config import settings
from app.domain.models.calendar import (
    CalendarControl,
    configure_calendar_control,
    get_calendar_control,
)
from app.domain.models.engine import EngineState
from app.domain.models.world import World
from app.infrastructure.api.dependencies import (
    get_engine_service,
    get_analytics_service,
    get_world_service,
    restore_checkpoint_state,
)
from app.infrastructure.repositories.supabase_checkpoints import SupabaseCheckpoints

router = APIRouter()


def save_failure_detail(error: httpx.HTTPError) -> str:
    """Expose safe categories, never upstream messages, payloads or credentials."""
    suffix = " Refresh saves before retrying; completion was not confirmed."
    if isinstance(error, httpx.TimeoutException):
        return "Supabase save timed out. The save may have completed." + suffix
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        try:
            code = error.response.json().get("code", "")
        except (ValueError, AttributeError):
            code = ""
        if status in {401, 403} or code == "42501":
            return "Supabase rejected save permissions. Check the backend server key and function grants." + suffix
        if code in {"PGRST202", "42883"}:
            return "A required Supabase save function is missing. Apply the complete-save and overwrite migrations." + suffix
        if code in {"42P01", "42703", "PGRST204"}:
            return "Supabase save schema is incomplete. Apply all repository migrations in order." + suffix
        if status == 413:
            return "The world save exceeds the server request-size limit." + suffix
        if code == "57014":
            return "Supabase stopped the save at its database statement timeout." + suffix
        if isinstance(code, str) and len(code) == 5 and code.isalnum():
            return f"Supabase rejected the save (database code {code}, HTTP {status})." + suffix
        return f"Supabase save request failed (HTTP {status})." + suffix
    return "Could not reach Supabase while saving. Check the network and retry after refreshing saves."


class RestorablePayload(BaseModel):
    """Validate the complete restore payload before mutating runtime state."""

    world: World
    calendar: CalendarControl
    tick_rate: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_daylight(self) -> "RestorablePayload":
        """Reject a clock configuration the runtime would refuse."""
        if self.calendar.night_start_hour - self.calendar.day_start_hour < 6:
            raise ValueError("Daytime must be at least six hours long")
        return self


def require_admin_token(request: Request, x_admin_token: str = Header(default="")) -> None:
    """Fail closed unless an explicit backend admin token matches."""
    if getattr(request.state, "hosted_owner_authenticated", False):
        return
    token = settings.CHECKPOINT_ADMIN_TOKEN.get_secret_value()
    if not token or not secrets.compare_digest(token, x_admin_token):
        raise HTTPException(401, "A valid X-Admin-Token is required")


def checkpoint_store(_: None = Depends(require_admin_token)) -> SupabaseCheckpoints:
    """Build checkpoint storage only after admin authentication."""
    try:
        return SupabaseCheckpoints(
            settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY.get_secret_value()
        )
    except ValueError as error:
        raise HTTPException(503, str(error)) from None


class CheckpointRequest(BaseModel):
    """Human-readable backup label."""

    label: str = Field(default="Manual checkpoint", min_length=1, max_length=120)
    include_archive: bool = False
    overwrite_id: UUID | None = None


@router.post("", status_code=201)
async def save_checkpoint(
    request: CheckpointRequest, store: SupabaseCheckpoints = Depends(checkpoint_store)
) -> dict:
    """Copy state before awaiting network I/O; require the simulation paused."""
    engine = get_engine_service()
    if engine.get_simulation_state() == EngineState.RUNNING:
        raise HTTPException(409, "Pause the simulation before creating a checkpoint")
    world = get_world_service().get_world()
    if world is None:
        raise HTTPException(409, "Create a world before saving a checkpoint")
    record = {
        "id": str(request.overwrite_id or uuid4()),
        "schema_version": 1,
        "label": request.label,
        "tick": engine.get_current_tick().value,
        "payload": {
            "world": world.model_dump(mode="json"),
            "calendar": get_calendar_control().model_dump(mode="json"),
            "tick_rate": engine.get_tick_rate(),
        },
    }
    try:
        if request.include_archive:
            analytics = get_analytics_service()
            archive = {
                "id": str(uuid4()), "world_seed": world.seed,
                "world_width": world.width, "world_height": world.height,
                "current_tick": record["tick"], "tick_rate": engine.get_tick_rate(),
                "calendar": record["payload"]["calendar"],
                "experiments": [item.model_dump(mode="json") for item in analytics.experiments()],
                "metrics": [item.model_dump(mode="json") for item in analytics.history(analytics.MAX_HISTORY)],
                "events": [item.model_dump(mode="json") for item in analytics.all_events()],
            }
            result = await store.overwrite(record, archive) if request.overwrite_id else await store.save_complete(record, archive)
        else:
            result = await store.overwrite(record, None) if request.overwrite_id else await store.save(record)
        return {key: value for key, value in result.items() if key != "payload"}
    except LookupError:
        raise HTTPException(404, "Selected save no longer exists. Refresh saves.") from None
    except ValueError:
        raise HTTPException(422, "World save exceeds the supported size or contains invalid data.") from None
    except httpx.HTTPError as error:
        raise HTTPException(502, save_failure_detail(error)) from None


@router.get("")
async def list_checkpoints(
    store: SupabaseCheckpoints = Depends(checkpoint_store),
) -> list:
    """List checkpoint metadata without transferring whole worlds."""
    try:
        return await store.read()
    except httpx.HTTPError:
        raise HTTPException(502, "Checkpoint storage request failed") from None


@router.get("/status")
async def checkpoint_status(
    store: SupabaseCheckpoints = Depends(checkpoint_store),
) -> dict:
    """Verify table access without saving a world or exposing server credentials."""
    try:
        await store.read()
    except httpx.HTTPStatusError as error:
        if error.response.status_code in {401, 403}:
            raise HTTPException(502, "Supabase rejected the server credentials or table permissions") from None
        raise HTTPException(502, "Supabase checkpoint table request failed; check the migration") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Supabase could not read the checkpoint table") from None
    return {"connected": True, "message": "Supabase checkpoint table is reachable (read access verified)."}


@router.get("/{checkpoint_id}")
async def read_checkpoint(
    checkpoint_id: UUID, store: SupabaseCheckpoints = Depends(checkpoint_store)
) -> dict:
    """Download a backup; does not mutate the active world."""
    try:
        records = await store.read(checkpoint_id)
    except ValueError:
        raise HTTPException(422, "Saved world payload is invalid or uses an unsupported encoding.") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Checkpoint storage request failed") from None
    if not records:
        raise HTTPException(404, "Checkpoint not found")
    return records[0]


@router.post("/{checkpoint_id}/restore")
async def restore_checkpoint(
    checkpoint_id: UUID, store: SupabaseCheckpoints = Depends(checkpoint_store)
) -> dict:
    """Restore a saved world and clock into a paused simulation."""
    try:
        records = await store.read(checkpoint_id)
    except ValueError:
        raise HTTPException(422, "Saved world payload is invalid or uses an unsupported encoding.") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Checkpoint storage request failed") from None
    if not records:
        raise HTTPException(404, "Checkpoint not found")
    record = records[0]
    if record.get("schema_version") != 1:
        raise HTTPException(422, "Unsupported checkpoint version")
    tick = record.get("tick")
    if type(tick) is not int or tick < 0:
        raise HTTPException(422, "Invalid checkpoint tick")
    try:
        payload = RestorablePayload.model_validate(record.get("payload"))
    except ValidationError:
        raise HTTPException(422, "Invalid checkpoint payload") from None
    try:
        restore_checkpoint_state(payload.world, tick, payload.tick_rate)
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from None
    configure_calendar_control(tick, payload.calendar)
    return {
        "checkpoint_id": str(checkpoint_id),
        "state": "PAUSED",
        "tick": tick,
        "message": "World restored. Reload the Godot world before resuming.",
    }
