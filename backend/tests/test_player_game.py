import time
from types import SimpleNamespace

from starlette.testclient import TestClient
from app import player_accounts as accounts
from app.domain.models.world import World
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.hosted import HostedBackend


def test_two_players_read_same_world_without_owner_access(monkeypatch):
    token = 'test-only-' + 'x' * 40
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN', token)
    world = World(width=8, height=8)
    residents = [Entity(kind=EntityKind.AGENT, name=name, x=i, y=2, needs=NeedsState(),
                        metadata={'account_user_id': name, 'player_chat': [{'content': 'secret-'+name}],
                                  'decision_trace': ['private-'+name]}) for i, name in enumerate(('Alice', 'Bob'))]
    world.entities = {str(e.id): e for e in residents}
    monkeypatch.setattr(accounts, 'linked_citizen', lambda uid: (None, world, next(e for e in residents if e.name == uid)))
    from starlette.applications import Starlette
    app = HostedBackend(Starlette(), token)
    client = TestClient(app, base_url='https://testserver')
    assert client.get('/account/game-data/world').status_code == 401
    for own in residents:
        client.cookies.set(accounts.COOKIE, accounts.seal({'uid': own.name, 'name': own.name, 'exp': time.time()+300}))
        response = client.get('/account/game-data/world?entity_id=ignored')
        assert response.status_code == 200
        data = response.json()
        assert data['player_entity_id'] == str(own.id)
        assert len(data['entities']) == 2
        assert 'secret-' not in response.text and 'account_user_id' not in response.text and 'private-' not in response.text
        for entity in data['entities']:
            assert ('needs' in entity) == (entity['id'] == str(own.id))
            assert ('player' in entity['tags']) == (entity['id'] == str(own.id))
        assert client.post('/account/game-data/world').status_code == 405
        for path in ('/api/v1/world', '/api/v1/entities/admin/overview', '/api/v1/checkpoints', '/admin/world'):
            assert client.get(path).status_code == 401
        for path in ('/api/v1/world/generate', '/api/v1/simulation/start', '/api/v1/entities'):
            assert client.post(path).status_code == 401
        shell = client.get('/game/')
        assert shell.status_code == 200
        assert 'window.AITIZEN_PLAYER = true' in shell.text
    monkeypatch.setattr(accounts, 'linked_citizen', lambda uid: (None, world, None))
    assert client.get('/account/game-data/world').status_code == 409
    client.cookies.set(accounts.COOKIE, accounts.seal({'uid': 'Alice', 'exp': time.time()-1}))
    assert client.get('/account/game-data/entities').status_code == 401
