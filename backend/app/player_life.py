"""Account-owned life history and directional relationship presentation."""
from app.player_dashboard import esc


def panels(user, world, entity):
    if entity is None or world is None:
        return ''
    episodes = sorted(world.episodes.get(str(entity.id), []), key=lambda e: (e.tick, str(e.id)), reverse=True)[:24]
    key = f"{user['uid']}:{getattr(world, 'seed', '')}:{entity.id}"
    rows = ''.join(
        f'<article class="memory life-event" data-tick="{e.tick}"><small class="muted">Tick {e.tick} · {esc(e.episode_type.value.title())}</small><p>{esc(e.summary)}</p></article>'
        for e in episodes
    )
    timeline = '<section class="panel" id="timeline" data-history-key="'+esc(key)+'"><span class="eyebrow">Your citizen’s story</span><h2>While you were away</h2><p id="visit-summary" class="muted">Latest recorded events · up to 24 entries</p>'+ (rows or '<p class="empty">No recorded events yet.</p>')+'</section>'
    cards = []
    for bond in sorted(getattr(world, 'social_bonds', {}).values(), key=lambda b: b.last_interaction_tick, reverse=True):
        if bond.source_id != entity.id:
            continue
        other = world.entities.get(str(bond.target_id))
        if other is None:
            continue
        label = 'Friend' if bond.trust >= .35 and bond.familiarity >= .25 else 'Strained' if bond.trust < 0 else 'Acquaintance'
        cards.append('<article class="relationship"><img class="bond-portrait" loading="lazy" src="/account/portrait/'+esc(other.avatar_id.value)+'" alt=""><strong>'+esc(other.name)+'</strong><span class="badge">'+label+'</span><p class="muted">Familiarity '+str(round(bond.familiarity*100))+'% · Trust '+str(round(bond.trust*100))+'%</p><small class="muted">'+str(bond.interactions)+' recorded interactions · Tick '+str(bond.last_interaction_tick)+'</small></article>')
        if len(cards) >= 12:
            break
    return timeline + '<section class="panel" id="relationships"><span class="eyebrow">People they know</span><h2>Relationships</h2><p class="muted">Your citizen’s recorded perspective</p>'+(''.join(cards) or '<p class="empty">Relationships appear after social encounters.</p>')+'</section>'


SCRIPT = r"""
(()=>{const panel=document.querySelector('#timeline');if(!panel)return;try{
 const key='realm-visit:'+panel.dataset.historyKey,events=[...panel.querySelectorAll('[data-tick]')];
 const stored=localStorage.getItem(key),last=stored===null?null:Number(stored),latest=Math.max(0,...events.map(e=>Number(e.dataset.tick)));
 let count=0;for(const e of events){if(last!==null&&Number(e.dataset.tick)>last){e.classList.add('new-event');count++;}}
 document.querySelector('#visit-summary').textContent=last===null?'Your latest recorded events · first visit on this browser':latest<last?'Earlier world checkpoint · showing recent history':count?count+' new events in the latest 24 entries since your last visit on this browser':'No newer events in the latest recorded history';
 localStorage.setItem(key,String(latest));
}catch(e){}})();
"""
