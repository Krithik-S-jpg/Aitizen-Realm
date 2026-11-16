"""Account-owned character edits; never accepts a target citizen ID."""
from pathlib import Path
from starlette.responses import RedirectResponse, FileResponse
from app.domain.models.entity import CitizenAvatar

APPEARANCES = [('juniper','Juniper'),('rowan','Rowan (new)'),('scout','Aster'),('builder','Ember'),('herbalist','Fern'),('scholar','Lumen'),('cook','Rowan'),('miner','Saffron'),('fisher','Tide'),('artisan','Violet')]


def form(entity):
    from app.player_dashboard import esc
    choices=''.join('<label class="look"><input type="radio" name="avatar_id" value="'+key+'" '+('checked' if entity.avatar_id.value==key else '')+'><img src="/account/portrait/'+key+'" alt="" width="70" height="90"><span>'+label+'</span></label>' for key,label in APPEARANCES)
    def options(values,current):
        return ''.join('<option value="'+v+'" '+('selected' if current==v else '')+'>'+v.title()+'</option>' for v in values)
    return '<section class="panel" id="customize"><span class="eyebrow">Character studio</span><h2>Make it yours</h2><p class="muted">Choose an appearance and a name for your citizen.</p><form method="post" action="/account/customize"><div class="studio-preview"><img id="studio-image" src="/account/portrait/'+esc(entity.avatar_id.value)+'" alt="Selected appearance"><div><h2 id="studio-name">'+esc(entity.name)+'</h2><span class="muted">Preview  -  changes apply when saved</span></div></div><label>Citizen name<input class="profile-input" name="name" value="'+esc(entity.name)+'" required maxlength="80"></label><div class="looks">'+choices+'</div><div class="needs"><label>Gender<select class="profile-input" name="gender">'+options(['unspecified','female','male','nonbinary'],entity.gender)+'</select></label><label>Food preference<select class="profile-input" name="diet">'+options(['omnivore','vegetarian'],entity.diet)+'</select></label></div><p class="footnote">Appearance and gender are independent. Age, health and world position stay unchanged.</p><div class="studio-actions"><button class="primary">Save character</button><button type="reset" class="quiet">Reset changes</button></div></form></section>'


async def customize(request):
    from app.player_accounts import identity, fields, linked_citizen
    from app.player_portal_design import dashboard
    user=identity(request)
    if not user:
        return RedirectResponse('/account',status_code=303)
    world=entity=None
    try:
        data=await fields(request)
        _,world,entity=linked_citizen(user['uid'])
        if entity is None:
            raise ValueError('Join the shared world before customizing a citizen.')
        name=data.get('name','').strip()
        avatar=CitizenAvatar(data.get('avatar_id',''))
        gender=data.get('gender','')
        diet=data.get('diet','')
        if not 1<=len(name)<=80 or any(ord(c)<32 for c in name):
            raise ValueError('Use a name between 1 and 80 characters, without control characters.')
        if gender not in ('unspecified','female','male','nonbinary') or diet not in ('omnivore','vegetarian'):
            raise ValueError('Choose a listed gender and food preference.')
        entity.name=name
        entity.avatar_id=avatar
        entity.gender=gender
        entity.diet=diet
        return RedirectResponse('/account?character=saved#customize',status_code=303)
    except ValueError:
        return dashboard(user,world,entity,notice='Character not saved. Check your choices and sign-in, then try again.')


async def portrait(request):
    from app.player_accounts import identity
    if not identity(request):
        return RedirectResponse('/account',status_code=303)
    key=request.path_params['avatar']
    if key not in dict(APPEARANCES):
        from starlette.responses import Response
        return Response(status_code=404)
    return FileResponse(Path(__file__).with_name('player_portraits')/(key+'.png'),headers={'Cache-Control':'private, max-age=86400'})
