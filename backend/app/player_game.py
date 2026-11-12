"""Read-only game projection. No owner endpoints or automatic world generation."""
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

# Explicit visual fields: never forward arbitrary citizen metadata or private chats.
VISUAL = set('id name kind x y avatar_id visual_avatar life_stage gender action action_progress action_target route route_status indoors sleep_home_position travel_mode underwater care_animation teaching_animation carried_by infant_carried_by carrying_infant carrying_casualty carried_avatar'.split())
METADATA = set('species state in_cave anchored home marine'.split())


def entity_view(entity, world, own):
    from app.infrastructure.api.v1.world import _format_entity
    full = _format_entity(entity, world)
    result = {key: value for key, value in full.items() if key in VISUAL}
    result['metadata'] = {key: value for key, value in entity.metadata.items() if key in METADATA}
    result['tags'] = ['player'] if entity.id == own.id else []
    if entity.id == own.id:
        for key in ('needs', 'inventory', 'goal', 'decision_reason', 'oxygen', 'depth', 'ai_mode'):
            result[key] = full.get(key)
    return result


async def data(request):
    from app.player_accounts import identity, linked_citizen
    from app.infrastructure.api.v1.world import _format_world, get_live_scene
    from app.infrastructure.api.dependencies import get_engine_service, get_world_service
    from app.infrastructure.api.v1.simulation import calendar_at_tick
    user = identity(request)
    headers = {'Cache-Control': 'no-store'}
    if not user:
        return JSONResponse({'detail': 'Session expired. Return to your account to sign in.'}, 401, headers=headers)
    try:
        _, world, own = linked_citizen(user['uid'])
        if own is None:
            raise ValueError('Your citizen is not in the loaded world. Return to your account.')
    except ValueError:
        return JSONResponse({'detail': 'Waiting for the administrator to load your world. Return to your account if this continues.'}, 409, headers=headers)
    section = request.path_params['section']
    if section == 'world':
        result = _format_world(world)
        result['entities'] = [entity_view(e, world, own) for e in world.entities.values() if e.active or e.id == own.id]
        result['player_entity_id'] = str(own.id)
    elif section == 'entities':
        result = [entity_view(e, world, own) for e in world.entities.values() if e.active or e.id == own.id]
    elif section == 'live':
        result = get_live_scene(get_world_service())
    elif section == 'state':
        engine = get_engine_service()
        tick = engine.get_current_tick().value
        result = {'state': engine.get_simulation_state(), 'current_tick': tick,
                  'tick_rate': engine.get_tick_rate(), 'calendar': calendar_at_tick(tick).model_dump(mode='json')}
    else:
        return JSONResponse({'detail': 'Not found'}, 404, headers=headers)
    return JSONResponse(jsonable_encoder(result), headers=headers)
