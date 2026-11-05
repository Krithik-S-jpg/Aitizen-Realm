"""Supabase identity verification and restricted player portal.

Player cookies never confer owner privileges. Account linkage lives in world
metadata and therefore travels with checkpoints. One backend worker is required.
"""
import base64
import hashlib
import hmac
import html
import json
import os
import secrets
import time
from urllib.parse import parse_qs, urlencode
from uuid import UUID

import httpx
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

COOKIE = '__Host-player'


def seal(data):
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    signature = hmac.new(os.environ['HOSTED_ADMIN_TOKEN'].encode(), ('player:'+payload).encode(), hashlib.sha256).hexdigest()
    return payload+'.'+signature


def unseal(value):
    try:
        payload, signature = value.rsplit('.', 1)
        expected = hmac.new(os.environ['HOSTED_ADMIN_TOKEN'].encode(), ('player:'+payload).encode(), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data if time.time() < data['exp'] else None
    except (ValueError, KeyError, TypeError):
        return None


def page(content, status=200):
    return HTMLResponse('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aitizen Realm accounts</title>
<style>body{background:#0c1721;color:#e2eeed;font:17px system-ui;max-width:560px;margin:7vh auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin:8px 0;border-radius:8px;border:1px solid #456b70;background:#18322f;color:white}a{color:#8bd9ca}small{color:#acbfc4}</style>'''+content,
        status_code=status, headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'"})


def config():
    from app.core.config import settings
    base = settings.SUPABASE_URL.rstrip('/')
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
    origin = os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')
    if not base.startswith('https://') or not key or not origin.startswith('https://'):
        raise ValueError('Account login is awaiting server configuration.')
    return base, key, origin


async def auth_call(path, body=None, token=None):
    base, key, _ = config()
    headers = {'apikey':key}
    if token:
        headers['Authorization'] = 'Bearer '+token
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request('GET' if body is None else 'POST', base+'/auth/v1/'+path, json=body, headers=headers)
    if response.status_code >= 400:
        raise ValueError('Authentication failed. Check your details and provider configuration.')
    return response.json()


async def fields(request):
    _, _, origin = config()
    if request.headers.get('origin') != origin:
        raise ValueError('Request origin rejected.')
    body = b''
    async for chunk in request.stream():
        body += chunk
        if len(body) > 8192:
            raise ValueError('Request too large.')
    return {key: values[0] for key, values in parse_qs(body.decode()).items()}


async def finish_login(tokens):
    user = await auth_call('user', token=tokens['access_token'])
    uid = str(UUID(user['id']))
    if not user.get('email_confirmed_at'):
        raise ValueError('Confirm your email before signing in.')
    name = str(user.get('user_metadata', {}).get('display_name') or user.get('user_metadata', {}).get('full_name') or 'Citizen')[:80]
    response = RedirectResponse('/account', status_code=303)
    response.set_cookie(COOKIE, seal({'uid':uid,'name':name,'exp':int(time.time())+3600}), max_age=3600, secure=True, httponly=True, samesite='strict')
    response.delete_cookie('__Host-oauth', secure=True, httponly=True, samesite='lax')
    return response


def identity(request):
    data = unseal(request.cookies.get(COOKIE, ''))
    return data if data and 'uid' in data else None


def linked_citizen(uid):
    from app.infrastructure.api.dependencies import get_entity_service
    service = get_entity_service()
    world = service._repository.get()
    if world is None:
        raise ValueError('The administrator must load the shared world first.')
    entity = next((e for e in world.entities.values() if e.metadata.get('account_user_id') == uid), None)
    return service, world, entity


async def account(request):
    user = identity(request)
    if not user:
        return page('''<h1>Join Aitizen Realm</h1><p>Your account, your citizen, one shared world.</p>
<form method="post" action="/account/password"><label>Email<input name="email" type="email" autocomplete="email" required></label><label>Password<input name="password" type="password" autocomplete="current-password" minlength="8" required></label><label>Citizen name (new accounts)<input name="name" maxlength="80"></label><button name="action" value="login">Sign in</button><button name="action" value="signup">Create account</button></form>
<p><a href="/account/google">Continue with Google</a></p><small>New email accounts require email confirmation.</small><p><a href="/login">Administrator sign-in</a></p>''')
    content = '<h1>Welcome, '+html.escape(user['name'])+'</h1>'
    try:
        _, _, entity = linked_citizen(user['uid'])
        if entity:
            content += '<p>Your citizen: '+html.escape(entity.name)+'</p><p>Status: '+('Active' if entity.active else 'Inactive')+'</p>'
        else:
            content += '<form method="post" action="/account/join"><button>Join the shared world</button></form>'
    except ValueError as error:
        content += '<p>'+html.escape(str(error))+'</p>'
    content += '<p>Player world controls are not enabled yet. Your administrator controls the simulation.</p><form method="post" action="/account/logout"><button>Sign out</button></form>'
    return page(content)


async def password(request):
    try:
        data = await fields(request)
        body = {'email':data.get('email',''), 'password':data.get('password','')}
        if data.get('action') == 'signup':
            body['data'] = {'display_name': data.get('name','Citizen')[:80]}
            await auth_call('signup', body)
            return page('<h1>Check your email</h1><p>If registration is available, follow the confirmation link, then return here to sign in.</p><a href="/account">Return to sign in</a>')
        return await finish_login(await auth_call('token?grant_type=password', body))
    except (ValueError, KeyError, httpx.HTTPError):
        return page('<h1>Unable to sign in</h1><p>Check your credentials, email confirmation, and account service configuration.</p><a href="/account">Try again</a>', 400)


async def google(request):
    try:
        base, _, origin = config()
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        response = RedirectResponse(base+'/auth/v1/authorize?'+urlencode({'provider':'google','redirect_to':origin+'/account/callback','code_challenge':challenge,'code_challenge_method':'s256'}))
        response.set_cookie('__Host-oauth', seal({'verifier':verifier,'exp':int(time.time())+600}), max_age=600, secure=True, httponly=True, samesite='lax')
        return response
    except ValueError as error:
        return page('<p>'+html.escape(str(error))+'</p><a href="/account">Back</a>', 503)


async def callback(request):
    try:
        pending = unseal(request.cookies.get('__Host-oauth',''))
        if not pending or not request.query_params.get('code'):
            raise ValueError('Expired sign-in')
        tokens = await auth_call('token?grant_type=pkce', {'auth_code':request.query_params['code'],'code_verifier':pending['verifier']})
        return await finish_login(tokens)
    except (ValueError, KeyError, httpx.HTTPError):
        return page('<p>Google sign-in did not complete. Please try again.</p><a href="/account">Back</a>', 400)


async def join(request):
    try:
        await fields(request)
        user = identity(request)
        if not user:
            return RedirectResponse('/account', status_code=303)
        # No awaits between lookup and creation: single-worker idempotent join.
        service, world, entity = linked_citizen(user['uid'])
        if entity is None:
            from app.domain.models.entity import EntityKind
            entity = service.create(EntityKind.AGENT, user['name'], world.width//2, world.height//2, auto_spawn=True)
            entity.metadata['account_user_id'] = user['uid']
        return RedirectResponse('/account', status_code=303)
    except ValueError as error:
        return page('<p>'+html.escape(str(error))+'</p><a href="/account">Back</a>', 409)


async def logout(request):
    try:
        await fields(request)
    except ValueError:
        return JSONResponse({'detail':'Origin rejected'}, status_code=403)
    response = RedirectResponse('/account', status_code=303)
    response.delete_cookie(COOKIE, secure=True, httponly=True, samesite='strict')
    return response


portal = Starlette(routes=[Route('/account',account), Route('/account/password',password,methods=['POST']), Route('/account/google',google), Route('/account/callback',callback), Route('/account/join',join,methods=['POST']), Route('/account/logout',logout,methods=['POST'])])
