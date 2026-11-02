"""Loopback-only feed for the outbound Observatory connector."""
import time
from fastapi import APIRouter, HTTPException, Request, Response
from app.application.services.observer_service import snapshot

router = APIRouter()
_picture = b""
_picture_at = 0.0
_lease_until = 0.0


def local(request):
    if request.client is None or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "Observer feed is loopback-only.")


@router.get("/snapshot")
async def observe(request: Request):
    local(request)
    global _lease_until
    _lease_until = time.time()+90
    from app.infrastructure.api import dependencies as d
    return snapshot(d._world_repository.get(), d._engine.get_current_tick().value, d._engine.get_state().value, d._analytics_service)


@router.get("/capture-status")
async def capture_status(request: Request):
    local(request)
    return {"enabled": time.time() < _lease_until, "captured_at": _picture_at}


@router.post("/picture")
async def receive_picture(request: Request):
    local(request)
    global _picture, _picture_at
    if time.time() > _lease_until:
        raise HTTPException(409, "No active observer connector")
    if time.time()-_picture_at < 20:
        raise HTTPException(429, "Capture rate limited")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 800000:
            raise HTTPException(413, "Image too large")
    if not body.startswith(b"\xff\xd8\xff"):
        raise HTTPException(415, "JPEG required")
    _picture, _picture_at = bytes(body), time.time()
    return {"accepted": True}


@router.get("/picture")
async def get_picture(request: Request):
    local(request)
    if not _picture:
        raise HTTPException(404, "No game capture received")
    return Response(_picture, media_type="image/jpeg", headers={"X-Captured-At": str(_picture_at), "Cache-Control": "no-store"})
