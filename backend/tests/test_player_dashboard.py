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
    live = client.get('/account/status?details=1&entity_id='+str(other.id)).json()
    assert live['citizen']['name'] == own.name
    assert live['citizen']['needs']['health'] == 100
    assert 'PRIVATE' not in str(live)
    own.needs.health = 42
    assert client.get('/account/status?details=1').json()['citizen']['needs']['health'] == 42
    own.needs.health = 100
    assert 'Follow my citizen' in response.text
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


def test_dashboard_waiting_and_arrival(monkeypatch):
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN','test-only-'+'x'*40)
    client=TestClient(accounts.portal,base_url='https://testserver')
    assert client.get('/account/arrival',follow_redirects=False).status_code==303
    client.cookies.set(accounts.COOKIE,accounts.seal({'uid':'owner','name':'<Player>','exp':time.time()+300}))
    def unavailable(uid):
        raise ValueError('The administrator must load the shared world first.')
    monkeypatch.setattr(accounts,'linked_citizen',unavailable)
    response=client.get('/account')
    assert response.status_code==200
    assert 'Shared world not set' in response.text
    assert 'id="conversation"' in response.text
    assert '&lt;Player&gt;' in response.text
    assert 'href="/game/"' not in response.text
    assert '<form method="post" action="/account/join"' not in response.text
    assert 'nonce-' in response.headers['content-security-policy']
    scene=client.get('/account/arrival')
    assert scene.status_code==200
    assert 'Interactive landscape' in scene.text
    assert 'engine.startGame' not in scene.text
    assert '$GODOT' not in scene.text


def test_character_customization_is_account_scoped(monkeypatch):
    from app.domain.models.entity import CitizenAvatar
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN','test-only-'+'x'*40)
    monkeypatch.setattr(accounts,'config',lambda: ('https://supabase.test','key','https://testserver'))
    world=World(width=32,height=32)
    own=Entity(kind=EntityKind.AGENT,name='Alice',x=12,y=12)
    other=Entity(kind=EntityKind.AGENT,name='Other',x=13,y=13)
    world.entities={str(own.id):own,str(other.id):other}
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid:(None,world,own))
    client=TestClient(accounts.portal,base_url='https://testserver')
    data={'name':'New name','avatar_id':'miner','gender':'female','diet':'vegetarian','entity_id':str(other.id)}
    assert client.post('/account/customize',data=data,follow_redirects=False).status_code==303
    assert own.name=='Alice'
    client.cookies.set(accounts.COOKIE,accounts.seal({'uid':'owner','name':'Alice','exp':time.time()+300}))
    client.post('/account/customize',data=data,headers={'origin':'https://evil.test'})
    assert own.name=='Alice'
    response=client.post('/account/customize',data=data,headers={'origin':'https://testserver'})
    assert response.status_code==200
    assert own.name=='New name' and own.avatar_id==CitizenAvatar.MINER
    assert own.gender=='female' and own.diet=='vegetarian'
    assert other.name=='Other' and (own.x,own.y)==(12,12)
    client.post('/account/customize',data={**data,'avatar_id':'invalid','name':'bad'},headers={'origin':'https://testserver'})
    assert own.name=='New name'
    assert Entity.model_validate_json(own.model_dump_json()).avatar_id==CitizenAvatar.MINER
    assert client.get('/account/portrait/miner').headers['content-type']=='image/png'


def test_godot_world_transport_stays_uncompressed():
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    from app.transport_compression import SimulationTransport
    payload={'tiles':[{'x':i,'terrain':'forest','walkable':True} for i in range(1000)]}
    async def endpoint(request):
        return JSONResponse(payload,headers={'Cache-Control':'no-store'})
    paths=['/account/game-data/world','/api/v1/world','/account/game-data/entities']
    client=TestClient(SimulationTransport(Starlette(routes=[Route(path,endpoint) for path in paths])))
    for path in paths:
        response=client.get(path,headers={'accept-encoding':'gzip, deflate, br'})
        assert 'content-encoding' not in response.headers
        assert response.headers['cache-control']=='no-store, no-transform'
        assert response.json()==payload
        assert int(response.headers['content-length'])==len(response.content)

def test_availability_status_is_account_scoped(monkeypatch):
    monkeypatch.setenv('HOSTED_ADMIN_TOKEN','test-only-'+'x'*40)
    client=TestClient(accounts.portal,base_url='https://testserver')
    assert client.get('/account/status').status_code==401
    client.cookies.set(accounts.COOKIE,accounts.seal({'uid':'owner','name':'Alice','exp':time.time()+300}))
    world=World(width=32,height=32)
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid:(None,world,None))
    r=client.get('/account/status')
    assert r.json()['loaded'] and not r.json()['joined']
    assert r.json()['status']=='World closed to new players'
    world.shared_world.accepting_players=True
    assert client.get('/account/status').json()['status']=='Ready to join'
    own=Entity(kind=EntityKind.AGENT,name='Private name',x=12,y=12)
    monkeypatch.setattr(accounts,'linked_citizen',lambda uid:(None,world,own))
    r=client.get('/account/status')
    assert r.json()['joined']
    assert 'Private name' not in r.text
    assert r.headers['cache-control']=='no-store'

def test_life_panels_show_only_own_recorded_history():
    from app.player_life import panels
    from app.domain.models.memory import Episode,EpisodeType
    from app.domain.models.society import SocialBond
    world=World(width=32,height=32)
    own=Entity(kind=EntityKind.AGENT,name='Alice',x=12,y=12)
    other=Entity(kind=EntityKind.AGENT,name='<Bob>',x=13,y=13)
    world.entities={str(own.id):own,str(other.id):other}
    world.episodes[str(own.id)]=[Episode(entity_id=own.id,episode_type=EpisodeType.DISCOVERY,tick=12,x=12,y=12,summary='<Found food>')]
    world.episodes[str(other.id)]=[Episode(entity_id=other.id,episode_type=EpisodeType.DANGER,tick=14,x=13,y=13,summary='PRIVATE HISTORY')]
    world.social_bonds['own']=SocialBond(source_id=own.id,target_id=other.id,trust=.5,familiarity=.4,interactions=4)
    text=panels({'uid':'owner'},world,own)
    assert '&lt;Found food&gt;' in text and 'PRIVATE HISTORY' not in text
    assert '&lt;Bob&gt;' in text and 'Friend' in text
    assert 'data-tick="12"' in text
