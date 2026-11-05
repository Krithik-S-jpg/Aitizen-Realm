"""Hosted browser sessions protect HTTP and WebSocket entry points."""
import os
import time

os.environ.setdefault("HOSTED_ADMIN_TOKEN", "test-only-" + "x" * 40)

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.hosted import HostedBackend

TOKEN = "test-only-" + "a" * 40
ORIGIN = {"Origin": "https://testserver"}

async def state(request):
    return JSONResponse({"ok": True})

async def socket(ws):
    await ws.accept()
    await ws.send_text("connected")
    await ws.close()

def test_sessions():
    app = HostedBackend(Starlette(routes=[Route('/state', state, methods=['GET','POST']), WebSocketRoute('/ws', socket)]), TOKEN)
    client = TestClient(app, base_url='https://testserver')
    assert client.get('/').url.path == '/login'
    assert client.get('/healthz').status_code == 200
    assert client.get('/state').status_code == 401
    assert client.post('/login', data={'key':TOKEN}).status_code == 403
    assert client.post('/login', data={'key':'wrong'}, headers=ORIGIN).status_code == 401
    response = client.post('/login', data={'key':TOKEN}, headers=ORIGIN, follow_redirects=False)
    assert response.status_code == 303
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=strict' in cookie
    assert TOKEN not in cookie
    assert client.get('/state').status_code == 200
    assert client.post('/state', headers={'Origin':'https://evil.example'}).status_code == 401
    assert client.post('/state', headers=ORIGIN).status_code == 200
    with client.websocket_connect('wss://testserver/ws', headers=ORIGIN) as ws:
        assert ws.receive_text() == 'connected'
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('wss://testserver/ws', headers={'Origin':'https://evil.example'}):
            pass
    assert not app.valid_cookie({b'cookie': ('__Host-aitizen='+app.session(int(time.time())-1)).encode()})
    assert not app.valid_cookie({b'cookie': b'__Host-aitizen=invalid'})
    client.post('/logout', headers=ORIGIN)
    assert client.get('/state').status_code == 401
    assert client.get('/state', headers={'Authorization':'Bearer '+TOKEN}).status_code == 200


def test_export_requires_login():
    from app.hosted import simulation_app, WEB_BUILD
    if not (WEB_BUILD / 'index.html').is_file():
        pytest.skip('Browser export not staged')
    client = TestClient(HostedBackend(simulation_app, TOKEN), base_url='https://testserver')
    assert client.get('/game/').url.path == '/login'
    assert client.get('/game/index.pck').status_code == 401
    client.post('/login', data={'key': TOKEN}, headers=ORIGIN, follow_redirects=False)
    response = client.get('/')
    assert response.url.path == '/game/'
    assert '<canvas' in response.text
    assert client.head('/game/index.wasm').status_code == 200
    assert client.get('/game/../../.env').status_code in (404, 400)

