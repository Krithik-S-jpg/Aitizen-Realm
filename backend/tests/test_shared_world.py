"""Shared-world designation is owner-only and survives checkpoint payloads."""
import os
from types import SimpleNamespace

os.environ.setdefault('HOSTED_ADMIN_TOKEN', 'test-only-'+'x'*40)
from starlette.applications import Starlette
from starlette.testclient import TestClient
from app.hosted import HostedBackend
from app.domain.models.world import World
from app.domain.models.entity import Entity, EntityKind
from app.infrastructure.api import dependencies


def test_world_designation_roundtrip():
    world = World(width=16,height=16)
    assert not world.shared_world.accepting_players
    world.shared_world.name = 'Our realm'
    world.shared_world.accepting_players = True
    citizen = Entity(kind=EntityKind.AGENT,name='Alice',x=1,y=1,tags={'autonomous'},metadata={'account_user_id':'verified-id','ai_mode':'utility'})
    world.entities[str(citizen.id)] = citizen
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.shared_world == world.shared_world
    assert restored.entities[str(citizen.id)].metadata['account_user_id'] == 'verified-id'
    assert 'autonomous' in restored.entities[str(citizen.id)].tags
    assert not World.model_validate({'width':16,'height':16}).shared_world.accepting_players


def test_only_owner_can_designate_current_world(monkeypatch):
    world = World(width=16,height=16,seed=42)
    monkeypatch.setattr(dependencies,'get_entity_service',lambda: SimpleNamespace(_repository=SimpleNamespace(get=lambda: world)))
    token = 'test-only-'+'a'*40
    client = TestClient(HostedBackend(Starlette(),token),base_url='https://testserver')
    assert client.get('/admin/world').status_code == 401
    assert client.post('/admin/world',data={'name':'Bad','open':'yes'}).status_code == 401
    client.post('/login',data={'key':token},headers={'origin':'https://testserver'},follow_redirects=False)
    assert client.get('/admin/login').url.path == '/admin/world'
    assert client.post('/admin/world',data={'name':'Bad','open':'yes'},headers={'origin':'https://evil.test'}).status_code == 401
    assert not world.shared_world.accepting_players
    response = client.post('/admin/world',data={'name':'Our realm','open':'yes'},headers={'origin':'https://testserver'})
    assert response.status_code == 200
    assert world.shared_world.accepting_players
    assert world.shared_world.name == 'Our realm'
    client.post('/admin/world',data={'name':'Our realm','open':'no'},headers={'origin':'https://testserver'})
    assert not world.shared_world.accepting_players
    assert client.post('/admin/world',data={'name':' '*3},headers={'origin':'https://testserver'}).status_code == 400
