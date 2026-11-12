"""Account-scoped dashboard, lightweight map and citizen chat."""
import html
from starlette.responses import HTMLResponse, RedirectResponse

def esc(value):
    return html.escape(str(value), quote=True)

STYLE = '''*{box-sizing:border-box}body{margin:0;background:#09191c;color:#e6eee5;font:16px system-ui}header,main{max-width:1280px;margin:auto;padding:24px}header{display:flex;justify-content:space-between;border-bottom:1px solid #294248}a{color:#aee1c5}h1{font:42px Georgia;margin:12px 0}h2{font:26px Georgia}small,.muted{color:#a2b6b5}.grid{display:grid;grid-template-columns:2fr 1fr;gap:24px}.card{background:#112a2e;border:1px solid #29494a;border-radius:20px;padding:24px;margin:20px 0}iframe{width:100%;height:650px;border:0;border-radius:16px;background:#102023}button{background:#c4dda0;border:0;border-radius:10px;color:#142a23;padding:14px 22px;font:inherit;cursor:pointer}textarea{width:100%;min-height:100px;background:#09191c;color:#fff;border:1px solid #486564;border-radius:10px;padding:14px;font:inherit}meter{width:100%;height:24px}.message{padding:14px;background:#193b3e;border-radius:12px;margin:12px 0;overflow-wrap:anywhere}.user{margin-left:24px;background:#285147}.stats{display:grid;grid-template-columns:1fr 1fr;gap:16px}svg{width:100%;max-height:370px}p{line-height:1.6}@media(max-width:800px){.grid{grid-template-columns:1fr}header,main{padding:16px}h1{font-size:32px}}'''

def document(body, refresh=False, status=200):
    return HTMLResponse('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+('<meta http-equiv="refresh" content="5">' if refresh else '')+'<title>My citizen · Aitizen Realm</title><style>'+STYLE+'</style></head><body>'+body+'</body></html>',status_code=status,headers={'Cache-Control':'no-store','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-src 'self'; form-action 'self'; frame-ancestors 'self'"})

def dashboard(user, world, entity):
    history=''.join('<div class="message '+('user' if m.get('role')=='user' else '')+'"><small>'+('You' if m.get('role')=='user' else esc(entity.name))+'</small><p>'+esc(m.get('content',''))+'</p></div>' for m in entity.metadata.get('player_chat',[])[-12:])
    return document('<header><strong>AITIZEN REALM / MY CITIZEN</strong><form method="post" action="/account/logout"><button>Sign out</button></form></header><main><small>'+esc(world.shared_world.name)+'</small><h1>Welcome, '+esc(user['name'])+'</h1><p class="muted">Your citizen lives autonomously. Follow their day and talk with them here.</p><div class="grid"><section class="card"><h2>Follow '+esc(entity.name)+'</h2><p class="muted">Live overhead map · follows your citizen · updates every 5 seconds</p><iframe title="Citizen map and live needs" src="/account/view"></iframe><p class="muted">Gold: your citizen · pale dots: residents and animals · squares: buildings. Surface terrain is shown, including when your citizen is diving or in a cave.</p></section><section class="card"><h2>Talk to your citizen</h2><p class="muted">Conversation does not issue commands. Without an available model, replies use simulation status.</p>'+history+'<form method="post" action="/account/chat"><label for="message">Your message</label><textarea id="message" name="message" maxlength="1000" required placeholder="How are you feeling?"></textarea><button>Send message</button></form><p><small>'+esc(entity.metadata.get('player_chat_source',''))+'</small></p></section></div></main>')

async def view(request):
    from app.player_accounts import identity, linked_citizen
    user=identity(request)
    if not user:
        return document('<main>Session expired. <a target="_top" href="/account">Sign in again</a>.</main>',status=401)
    try:
        _,world,entity=linked_citizen(user['uid'])
        if entity is None: raise ValueError('Your citizen is not in the loaded world.')
    except ValueError as error:
        return document('<main><p>'+esc(error)+'</p><a target="_top" href="/account">Return to account</a></main>',True)
    x0,y0=entity.x-12,entity.y-12
    colors={'WATER':'#327b91','OCEAN':'#23566d','FOREST':'#285a45','SAND':'#bca36c','MOUNTAIN':'#737d7a','STONE':'#64716a','SNOW':'#d5e1dd','DIRT':'#86634b'}
    shapes=[]
    for y in range(y0,y0+25):
        for x in range(x0,x0+25):
            tile=world.retrieve_tile(x,y)
            if tile: shapes.append(f'<rect x="{x-x0}" y="{y-y0}" width="1" height="1" fill="{colors.get(tile.terrain.value,"#487954")}"/>')
    for building in world.structures.values():
        if x0<=building.x<x0+25 and y0<=building.y<y0+25:
            shapes.append(f'<rect x="{building.x-x0+.15}" y="{building.y-y0+.15}" width=".7" height=".7" fill="#dbb383"/>')
    for other in world.entities.values():
        if other.active and x0<=other.x<x0+25 and y0<=other.y<y0+25 and other is not entity:
            shapes.append(f'<circle cx="{other.x-x0+.5}" cy="{other.y-y0+.5}" r=".22" fill="#e5eee7"/>')
    shapes.append('<circle cx="12.5" cy="12.5" r=".42" fill="#ffe095" stroke="#172522" stroke-width=".12"/>')
    state=str(entity.metadata.get('state','idle'))
    if entity.metadata.get('in_cave'): state='Exploring a cave'
    elif entity.metadata.get('dive_trip'): state='Diving'
    action=world.actions.get(world.active_actions.get(str(entity.id),''))
    if action and state=='idle': state=action.action_type.value
    bars=''
    if entity.needs:
        for label in ('health','energy','hunger','thirst'):
            value=float(getattr(entity.needs,label))
            bars+=f'<div>{label.title()} {value:.0f}/100<meter min="0" max="100" value="{value}" aria-label="{label}"></meter></div>'
    return document('<main><strong>'+esc(entity.name)+' · '+('Active' if entity.active else 'Inactive')+'</strong><p>'+esc(state.replace('_',' '))+' · Location '+str(entity.x)+', '+str(entity.y)+'</p><svg role="img" aria-label="Terrain and inhabitants centered on your citizen" viewBox="0 0 25 25">'+''.join(shapes)+'</svg><div class="stats">'+bars+'</div><small>Hunger and thirst: lower is better. The map changes only while the simulation advances.</small></main>',True)

async def chat(request):
    from app.player_accounts import identity, fields, linked_citizen
    from app.infrastructure.api.v1.entities import player_chat, PlayerChatRequest
    from fastapi import HTTPException
    user=identity(request)
    if not user: return RedirectResponse('/account',status_code=303)
    try:
        data=await fields(request)
        message=data.get('message','').strip()
        if not 1<=len(message)<=1000: raise ValueError('Write a message between 1 and 1000 characters.')
        service,_,entity=linked_citizen(user['uid'])
        if entity is None or not entity.active: raise ValueError('A living citizen in the loaded world is required.')
        result=await player_chat(entity.id,PlayerChatRequest(message=message),service)
        entity.metadata['player_chat_source']=result['source']
        return RedirectResponse('/account',status_code=303)
    except (ValueError,HTTPException) as error:
        return document('<main><h1>Message not sent</h1><p>'+esc(getattr(error,'detail',str(error)))+'</p><a href="/account">Return to your citizen</a></main>',status=409)
