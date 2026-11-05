"""Protected backend-only deployment entry point.

The public health probe reveals no simulation data. All other HTTP and
WebSocket requests require the owner token; missing configuration fails closed.
"""

import os
import secrets
import hashlib
import hmac
import time
from pathlib import Path
from http.cookies import CookieError, SimpleCookie
from urllib.parse import parse_qs

from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from app.main import app as simulation_app

WEB_BUILD = Path(__file__).resolve().parents[1] / "web"
if (WEB_BUILD / "index.html").is_file():
    simulation_app.mount("/game", StaticFiles(directory=WEB_BUILD, html=True), name="hosted-game")


class HostedBackend:
    """Guard the entire ASGI application, including WebSockets."""

    def __init__(self, wrapped, token: str):
        if len(token) < 32:
            raise RuntimeError("HOSTED_ADMIN_TOKEN must contain at least 32 characters")
        self.wrapped = wrapped
        self.token = token

    def session(self, expiry):
        """Sign a session without exposing the owner credential."""
        signature = hmac.new(self.token.encode(), f"browser:{expiry}".encode(), hashlib.sha256).hexdigest()
        return f"{expiry}.{signature}"

    def valid_cookie(self, headers):
        """Reject expired or modified sessions."""
        try:
            cookies = SimpleCookie()
            cookies.load(headers.get(b"cookie", b"").decode())
            value = cookies["__Host-aitizen"].value
            expiry = int(value.split(".")[0])
            return time.time() < expiry <= time.time() + 43200 and secrets.compare_digest(value, self.session(expiry))
        except (KeyError, ValueError, UnicodeError, CookieError):
            return False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.wrapped(scope, receive, send)
        if scope["type"] == "http" and scope["path"] == "/healthz" and scope["method"] == "GET":
            return await JSONResponse({"status": "ok"})(scope, receive, send)
        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"authorization", b"")
        expected = ("Bearer " + self.token).encode()
        bearer = secrets.compare_digest(supplied, expected)
        cookie = self.valid_cookie(headers)
        host = headers.get(b"host", b"").decode()
        origin = headers.get(b"origin", b"").decode()
        same_origin = origin == "https://" + host
        path = scope["path"]
        method = scope.get("method", "")
        if scope["type"] == "http" and path == "/login" and method == "GET":
            response = HTMLResponse('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aitizen Realm — Sign in</title><style>body{background:#0d1823;color:#e6f3f1;font:18px system-ui;max-width:480px;margin:12vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin:12px 0;background:#19362f;color:white;border:1px solid #69baa5;border-radius:8px}</style>
<h1>Aitizen Realm</h1><p>Sign in to your hosted simulation.</p>
<form method="post" action="/login"><label for="key">Owner access key</label><input id="key" name="key" type="password" required autocomplete="current-password"><button>Sign in</button></form>''', headers={"Cache-Control":"no-store", "Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'"})
            return await response(scope, receive, send)
        if scope["type"] == "http" and path == "/login" and method == "POST":
            if not same_origin:
                return await JSONResponse({"detail":"Origin rejected"}, status_code=403)(scope, receive, send)
            body = b""
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body += message.get("body", b"")
                if len(body) > 4096:
                    return await JSONResponse({"detail":"Request too large"}, status_code=413)(scope, receive, send)
                if not message.get("more_body"):
                    break
            key = parse_qs(body.decode(errors="replace")).get("key", [""])[0]
            if not secrets.compare_digest(key.encode(), self.token.encode()):
                return await JSONResponse({"detail":"Invalid owner key"}, status_code=401)(scope, receive, send)
            response = RedirectResponse("/", status_code=303, headers={"Cache-Control":"no-store"})
            response.set_cookie("__Host-aitizen", self.session(int(time.time()) + 43200), max_age=43200, secure=True, httponly=True, samesite="strict", path="/")
            return await response(scope, receive, send)
        if cookie and not bearer and (scope["type"] == "websocket" or method not in ("GET", "HEAD", "OPTIONS")) and not same_origin:
            cookie = False
        if not bearer and not cookie:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            if path in ("/", "/game", "/game/") and method == "GET":
                return await RedirectResponse("/login", status_code=303)(scope, receive, send)
            return await JSONResponse(
                {"detail": "Owner authentication required"}, status_code=401,
                headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
            )(scope, receive, send)
        if scope["type"] == "http" and path == "/logout" and method == "POST":
            response = RedirectResponse("/login", status_code=303)
            response.delete_cookie("__Host-aitizen", secure=True, httponly=True, samesite="strict")
            return await response(scope, receive, send)
        if scope["type"] == "http" and path == "/" and method == "GET":
            if (WEB_BUILD / "index.html").is_file():
                return await RedirectResponse("/game/", status_code=303)(scope, receive, send)
            return await HTMLResponse('<title>Aitizen Realm</title><h1>Backend connected</h1><p>You are signed in. Browser game deployment and the local Ollama worker are the next steps.</p><p><a href="/api/v1/simulation/state">View simulation status</a></p><form method="post" action="/logout"><button>Sign out</button></form>', headers={"Cache-Control":"no-store"})(scope, receive, send)
        await self.wrapped(scope, receive, send)


app = HostedBackend(simulation_app, os.environ.get("HOSTED_ADMIN_TOKEN", ""))
