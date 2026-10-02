from app.application.services.danger_memory import memory_graph
from app.domain.models.memory import Episode, EpisodeType
from app.domain.models.entity import EntityKind
from tests.test_decisions import _systems


def test_highlights_exclude_routine_deduplicate_and_preserve_raw_memories():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    citizen = entities.create(EntityKind.AGENT, "Observer", 5, 5)
    episodes = [
        Episode(entity_id=citizen.id, episode_type=EpisodeType.ACTION_RESULT,
                tick=1, x=5, y=5, summary="move completed", importance=1,
                details={"succeeded": True}),
        Episode(entity_id=citizen.id, episode_type=EpisodeType.ACTION_RESULT,
                tick=2, x=5, y=5, summary="build completed", importance=0.5,
                details={"succeeded": True}),
    ]
    for tick in range(3, 20):
        episodes.append(Episode(entity_id=citizen.id, episode_type=EpisodeType.DANGER,
                                tick=tick, x=5, y=5, summary="Wolf attack", importance=1))
    world.episodes[str(citizen.id)] = episodes
    result = memory_graph(world, citizen)
    assert len(result) == 2
    assert result[-1]["tick"] == 19
    assert len(world.episodes[str(citizen.id)]) == 19
