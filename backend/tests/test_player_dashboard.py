import time
from types import SimpleNamespace
from starlette.testclient import TestClient
from app import player_accounts as accounts
from app.domain.models.world import World
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.application.services.entity_service import EntityService


def test_dashboard_scopes_map_and_chat(monkeypatch):
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN','test-only-'+'x'*40)
    monkeypatch.setattr(accounts,'config',lambda: ('https://supabase.test','key','https://testserver'))
    world=World(width=32,height=32)
    own=Entity(kind=EntityKind.AGENT,name='<Alice>',x=12,y=12,needs=NeedsState())
    other=Entity(kind=EntityKind.AGENT,name='Other',x=13,y=13,metadata={'player_chat':[{'role':'user','content':'PRIVATE'}]})
    world.entities={str(own.id):own,str(other.id):other}
    service=EntityService(SimpleNamespace(get=lambda:world))
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid:(service,world,own))
    client=TestClient(accounts.portal,base_url='https://testserver')
    assert client.get('/account/view').status_code==401
    client.cookies.set(accounts.COOKIE,accounts.seal({'uid':'owner','name':'Alice','exp':time.time()+300}))
    response=client.get('/account')
    assert 'Talk to your citizen' in response.text
    assert '&lt;Alice&gt;' in response.text
    assert 'PRIVATE' not in response.text
    response=client.get('/account/view?entity_id='+str(other.id))
    assert 'Health 100/100' in response.text
    assert '&lt;Alice&gt;' in response.text
    assert client.post('/account/chat',data={'message':'Hi'},headers={'origin':'https://evil.test'}).status_code==409
    from app.application.services import player_chat
    async def reply(entity,message,model):
        assert entity is own
        return {'reply':'Hello','source':'Test status'}
    monkeypatch.setattr(player_chat,'reply',reply)
    response=client.post('/account/chat',data={'message':'Hi','entity_id':str(other.id)},headers={'origin':'https://testserver'})
    assert response.status_code==200
    assert own.metadata['player_chat'][-1]['content']=='Hello'
    assert len(other.metadata['player_chat'])==1
    own.active=False
    assert client.post('/account/chat',data={'message':'Hi'},headers={'origin':'https://testserver'}).status_code==409
