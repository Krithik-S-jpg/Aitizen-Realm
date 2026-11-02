"""Optional single-process recovery lifecycle; never resumes a world unattended."""

import asyncio
import logging

from app.core.config import settings
from app.domain.models.calendar import configure_calendar_control, get_calendar_control
from app.infrastructure.repositories.local_recovery import LocalRecovery, RecoveryState

logger = logging.getLogger(__name__)
status = {"state": "disabled", "last_saved_tick": None, "restored_tick": None}


async def save_recovery(tick: int, *, force: bool = False) -> None:
    if not settings.LOCAL_RECOVERY_ENABLED:
        return
    interval = max(1, settings.LOCAL_RECOVERY_INTERVAL_TICKS)
    if not force and (tick % interval or status["last_saved_tick"] == tick):
        return
    from app.infrastructure.api.dependencies import get_world_service, get_engine_service
    world = get_world_service().get_world()
    if world is None:
        return
    try:
        # Serialize synchronously at a completed-tick boundary, before yielding.
        payload = RecoveryState(world=world, tick=tick, tick_rate=get_engine_service().get_tick_rate(), calendar=get_calendar_control()).model_dump_json()
        await asyncio.to_thread(LocalRecovery(settings.LOCAL_RECOVERY_PATH).write_payload, payload)
        status.update(state="saved", last_saved_tick=tick)
    except Exception:
        status["state"] = "save_failed"
        logger.exception("Local recovery failed; previous generation retained")


async def restore_recovery() -> None:
    if not settings.LOCAL_RECOVERY_ENABLED:
        return
    from app.infrastructure.api.dependencies import get_world_service, restore_checkpoint_state
    if get_world_service().get_world() is not None:
        return
    try:
        state = await asyncio.to_thread(LocalRecovery(settings.LOCAL_RECOVERY_PATH).read)
        if state is None:
            status["state"] = "ready"
            return
        restore_checkpoint_state(state.world, state.tick, state.tick_rate)
        configure_calendar_control(state.tick, state.calendar)
        status.update(state="restored_paused", restored_tick=state.tick)
    except Exception:
        status["state"] = "restore_failed"
        # Do not start a blank timeline that might overwrite a recoverable save.
        raise RuntimeError("Local recovery failed; repair or explicitly disable recovery before startup") from None
