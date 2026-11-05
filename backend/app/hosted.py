"""Protected backend-only deployment entry point.

The public health probe reveals no simulation data. All other HTTP and
WebSocket requests require the owner token; missing configuration fails closed.
"""

import os
import secrets

from starlette.responses import JSONResponse

from app.main import app as simulation_app


class HostedBackend:
    """Guard the entire ASGI application, including WebSockets."""

    def __init__(self, wrapped, token: str):
        if len(token) < 32:
            raise RuntimeError("HOSTED_ADMIN_TOKEN must contain at least 32 characters")
        self.wrapped = wrapped
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.wrapped(scope, receive, send)
        if scope["type"] == "http" and scope["path"] == "/healthz" and scope["method"] == "GET":
            return await JSONResponse({"status": "ok"})(scope, receive, send)
        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"authorization", b"")
        expected = ("Bearer " + self.token).encode()
        if not secrets.compare_digest(supplied, expected):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            return await JSONResponse(
                {"detail": "Owner authentication required"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
            )(scope, receive, send)
        await self.wrapped(scope, receive, send)


app = HostedBackend(simulation_app, os.environ.get("HOSTED_ADMIN_TOKEN", ""))
