"""Player identities cannot become owner sessions or duplicate citizens."""
import os
import time
from types import SimpleNamespace

os.environ.setdefault('HOSTED_ADMIN_TOKEN', 'test-only-'+'x'*40)
from starlette.testclient import TestClient
from app import player_accounts as accounts
from app.hosted import HostedBackend
from starlette.applications import Starlette


def test_player_session_is_not_admin(monkeypatch):
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN', 'test-only-'+'x'*40)
    client = TestClient(HostedBackend(Starlette(), os.environ['HOSTED_ADMIN_TOKEN']), base_url='https://testserver')
    signed = accounts.seal({'uid':'test-user','name':'Citizen','exp':time.time()+3600})
    client.cookies.set(accounts.COOKIE, signed)
    assert client.get('/api/v1/simulation/state').status_code == 401
    assert accounts.unseal(signed)['uid'] == 'test-user'
    assert accounts.unseal(signed+'x') is None
    assert accounts.unseal(accounts.seal({'exp':time.time()-1})) is None


def test_repeat_join_reuses_citizen(monkeypatch):
    monkeypatch.setattr(accounts, 'config', lambda: ('https://supabase.test','public-key','https://testserver'))
    created = []
    class Service:
        def create(self, *args, **kwargs):
            citizen = SimpleNamespace(name='Citizen',metadata={},active=True,tags=kwargs['tags'])
            created.append(citizen)
            return citizen
    monkeypatch.setattr(accounts, 'linked_citizen', lambda uid: (Service(),SimpleNamespace(width=64,height=64,shared_world=SimpleNamespace(accepting_players=True)),created[0] if created else None))
    client = TestClient(accounts.portal, base_url='https://testserver')
    client.cookies.set(accounts.COOKIE, accounts.seal({'uid':'test-user','name':'Citizen','exp':time.time()+3600}))
    for _ in range(2):
        assert client.post('/account/join',headers={'origin':'https://testserver'},follow_redirects=False).status_code == 303
    assert len(created) == 1
    assert created[0].metadata['account_user_id'] == 'test-user'
    assert 'autonomous' in created[0].tags
    assert created[0].metadata['ai_mode'] == 'utility'
    assert client.post('/account/join',headers={'origin':'https://evil.test'}).status_code == 409


def test_password_navigation_returns_to_form(monkeypatch):
    async def unexpected_auth(*args, **kwargs):
        raise AssertionError('Navigation must not authenticate')
    monkeypatch.setattr(accounts, 'auth_call', unexpected_auth)
    client = TestClient(accounts.portal, base_url='https://testserver')
    for method in ('GET', 'HEAD'):
        response = client.request(method, '/account/password', follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/account'
        assert 'set-cookie' not in response.headers
    response = client.get('/account/password')
    assert response.status_code == 200
    assert response.url.path == '/account'
    assert 'Continue with Google' in response.text


def test_google_pkce_and_password_verification(monkeypatch):
    joins = []
    monkeypatch.setattr(accounts, 'ensure_citizen', lambda uid, name: joins.append((uid,name)))
    monkeypatch.setattr(accounts, 'config', lambda: ('https://supabase.test','public-key','https://testserver'))
    client = TestClient(accounts.portal, base_url='https://testserver')
    response = client.get('/account/google',follow_redirects=False)
    assert 'code_challenge=' in response.headers['location']
    assert 'code_challenge_method=s256' in response.headers['location']
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.get('/account/callback').status_code == 400
    async def fake_auth(path, body=None, token=None):
        if path.startswith('token'):
            return {'access_token':'verified-upstream'}
        assert token == 'verified-upstream'
        return {'id':'12345678-1234-1234-1234-123456789012','email_confirmed_at':'today','user_metadata':{'display_name':'Alice'}}
    monkeypatch.setattr(accounts,'auth_call',fake_auth)
    response = client.post('/account/password',data={'email':'alice@example.com','password':'test-password'},headers={'origin':'https://testserver'},follow_redirects=False)
    assert response.status_code == 303
    assert 'verified-upstream' not in response.headers['set-cookie']
    assert joins == [('12345678-1234-1234-1234-123456789012','Alice')]


def test_closed_world_and_inactive_citizen(monkeypatch):
    import pytest
    world = SimpleNamespace(shared_world=SimpleNamespace(accepting_players=False))
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid: (None,world,None))
    with pytest.raises(ValueError,match='not opened'):
        accounts.ensure_citizen('uid','Citizen')
    entity = SimpleNamespace(active=False,tags=set())
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid: (None,world,entity))
    assert accounts.ensure_citizen('uid','Citizen') is entity
    assert not entity.tags


def test_google_callback_creates_usable_player_session(monkeypatch):
    monkeypatch.setattr(accounts,'config',lambda: ('https://supabase.test','public-key','https://testserver'))
    monkeypatch.setattr(accounts,'ensure_citizen',lambda uid,name: None)
    world = SimpleNamespace(shared_world=SimpleNamespace(name='Our realm',accepting_players=True))
    citizen = SimpleNamespace(name='Alice',active=True,metadata={})
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid: (None,world,citizen))
    calls = []
    async def fake_auth(path, body=None, token=None):
        calls.append(path)
        if path == 'token?grant_type=pkce':
            assert body['auth_code'] == 'test-code'
            assert len(body['code_verifier']) >= 43
            return {'access_token':'upstream-secret'}
        assert token == 'upstream-secret'
        return {'id':'12345678-1234-1234-1234-123456789012','email_confirmed_at':'today','user_metadata':{'full_name':'Alice'}}
    monkeypatch.setattr(accounts,'auth_call',fake_auth)
    client = TestClient(accounts.portal,base_url='https://testserver')
    client.get('/account/google',follow_redirects=False)
    response = client.get('/account/callback?code=test-code',follow_redirects=False)
    assert response.status_code == 303
    cookie = next(c for c in response.headers.get_list('set-cookie') if c.startswith(accounts.COOKIE+'='))
    assert 'SameSite=lax' in cookie
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'Path=/' in cookie
    assert 'upstream-secret' not in cookie
    assert 'Welcome, Alice' in client.get('/account').text
    assert client.post('/account/logout',headers={'origin':'https://evil.test'}).status_code == 403
    assert 'Welcome, Alice' in client.get('/account').text
    assert client.post('/account/logout',headers={'origin':'https://testserver'},follow_redirects=False).status_code == 303
    assert 'Continue with Google' in client.get('/account').text
    assert calls == ['token?grant_type=pkce','user']
