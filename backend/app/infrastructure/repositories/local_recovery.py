"""Versioned, checksummed local recovery files with atomic replacement."""

import gzip
import hashlib
import json
import os
import zlib
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.domain.models.calendar import CalendarControl
from app.domain.models.world import World


class RecoveryState(BaseModel):
    version: int = 1
    tick: int = Field(ge=0)
    tick_rate: float = Field(gt=0, allow_inf_nan=False)
    calendar: CalendarControl
    world: World

    @model_validator(mode="after")
    def validate_state(self):
        if self.version != 1:
            raise ValueError("Unsupported recovery version")
        if self.calendar.night_start_hour - self.calendar.day_start_hour < 6:
            raise ValueError("Invalid daylight settings")
        return self


class LocalRecovery:
    """Single-writer local store; never used as a replacement for cloud backups."""

    def __init__(self, path: Path):
        self.path = path
        self.previous = path.with_suffix(path.suffix + ".previous")

    @staticmethod
    def decode(raw: bytes) -> RecoveryState:
        envelope = json.loads(gzip.decompress(raw))
        if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), str):
            raise ValueError("Invalid recovery envelope")
        payload = envelope["payload"]
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if digest != envelope["sha256"]:
            raise ValueError("Recovery checksum mismatch")
        return RecoveryState.model_validate_json(payload)

    def read(self) -> RecoveryState | None:
        failures = []
        for candidate in (self.path, self.previous):
            if not candidate.exists():
                continue
            try:
                return self.decode(candidate.read_bytes())
            except (ValueError, KeyError, OSError, EOFError, zlib.error) as error:
                failures.append(error)
        if failures:
            raise ValueError("No valid recovery generation; existing files preserved") from failures[0]
        return None

    @staticmethod
    def atomic_write(path: Path, raw: bytes) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def write_payload(self, payload: str) -> None:
        """Accept an immutable snapshot taken on the simulation event loop."""
        RecoveryState.model_validate_json(payload)
        envelope = {"payload": payload, "sha256": hashlib.sha256(payload.encode()).hexdigest()}
        raw = gzip.compress(json.dumps(envelope).encode())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            old = self.path.read_bytes()
            try:
                self.decode(old)
            except (ValueError, KeyError, OSError, EOFError, zlib.error):
                pass  # Never replace the good fallback with a corrupt generation.
            else:
                self.atomic_write(self.previous, old)
        self.atomic_write(self.path, raw)
