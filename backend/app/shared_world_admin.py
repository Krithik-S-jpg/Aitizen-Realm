"""Owner-only shared-world settings; called behind HostedBackend authorization."""
import html
from urllib.parse import parse_qs

from starlette.responses import RedirectResponse
from app.auth_design import realm_page


async def shared_world_page(scope, receive, send):
    from app.infrastructure.api.dependencies import get_entity_service
    world = get_entity_service()._repository.get()
    if world is None:
        return await realm_page('<h1>Choose your shared world</h1><p>Open the game and create or load the world you want players to join, then return here.</p><a class="google" href="/game/">Open game</a>')(scope, receive, send)
    if scope['method'] == 'POST':
        body = b''
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body += message.get('body', b'')
            if len(body) > 4096:
                return await realm_page('<p>Request too large.</p>',413)(scope,receive,send)
            if not message.get('more_body'):
                break
        values = parse_qs(body.decode(errors='replace'))
        name = values.get('name',['Shared realm'])[0].strip()
        if not name or len(name) > 80:
            return await realm_page('<p>Use a world name between 1 and 80 characters.</p><a href="/admin/world">Back</a>',400)(scope,receive,send)
        world.shared_world.name = name
        world.shared_world.accepting_players = values.get('open',['no'])[0] == 'yes'
        return await RedirectResponse('/admin/world?saved=1',status_code=303)(scope,receive,send)
    count = sum(1 for e in world.entities.values() if e.metadata.get('account_user_id'))
    name = html.escape(world.shared_world.name, quote=True)
    status = 'Open to new players' if world.shared_world.accepting_players else 'Closed to new players'
    content = f'''<span class="eyebrow">Realm administration</span><h1>One world. Everyone’s story.</h1>
<p>Currently loaded: {world.width} × {world.height} tiles · Seed {world.seed}<br>{count} linked citizens · {status}</p>
<form method="post" action="/admin/world"><label>Shared world name<input name="name" maxlength="80" value="{name}" required></label>
<button name="open" value="yes">Set this world and open player joins</button><button name="open" value="no">Save name and close new joins</button></form>
<small>New sign-ins receive one autonomous citizen in this world. Returning players keep their citizen. Closing joins does not remove existing citizens.</small>
<p>After changing this setting, pause and save the world in game Settings. Load that save after a server restart to restore the designation and citizen links.</p>
<a class="google" href="/game/">Return to the game</a><a class="admin-link" href="/account">Player portal</a>'''
    return await realm_page(content)(scope,receive,send)
