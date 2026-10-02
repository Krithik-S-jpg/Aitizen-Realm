"""Personal danger episodes, witnessed attacks and bounded fear recall."""

from uuid import NAMESPACE_URL, uuid5

from app.domain.models.entity import EntityKind
from app.domain.models.memory import Episode, EpisodeType


def sheltered(world, citizen) -> bool:
    home = world.structures.get(str(citizen.metadata.get("sleep_home_id", "")))
    return bool(home and home.completed and str(citizen.id) in home.resident_ids
                and citizen.metadata.get("indoors") and citizen.metadata.get("state") == "sleep"
                and citizen.distance_squared_to(home.x, home.y) <= 2)


def remember_attack(world, attacker, victim, tick):
    event_id = str(uuid5(NAMESPACE_URL, f"attack:{attacker.id}:{victim.id}:{tick}"))
    species = str(attacker.metadata.get("species", "animal"))
    for observer in world.entities.values():
        if observer.kind != EntityKind.AGENT or not observer.active:
            continue
        direct = observer.id == victim.id
        if not direct and (observer.metadata.get("state") == "sleep"
                           or observer.distance_squared_to(victim.x, victim.y) > observer.perception_radius ** 2):
            continue
        if not direct and not _visible(world, observer, victim):
            continue
        episode = Episode(
            id=uuid5(NAMESPACE_URL, event_id + str(observer.id)), entity_id=observer.id,
            episode_type=EpisodeType.DANGER, tick=tick, x=victim.x, y=victim.y,
            summary=f"{'Attacked by' if direct else 'Witnessed an attack by'} a {species}.",
            importance=1.0 if direct else 0.85, participants=[attacker.id, victim.id],
            details={"event_id": event_id, "attacker_id": str(attacker.id), "victim_id": str(victim.id),
                     "attacker_name": attacker.name, "victim_name": victim.name,
                     "species": species, "experience": "attacked" if direct else "witnessed",
                     "consequence": "Avoid this location and seek safety", "fear_gain": 65 if direct else 45},
        )
        episodes = world.episodes.setdefault(str(observer.id), [])
        if any(item.id == episode.id for item in episodes[-16:]):
            continue
        episodes.append(episode)
        if len(episodes) > 200:
            del episodes[:-200]
        observer.metadata.update(fear=min(100, fear_at(observer, tick) + episode.details["fear_gain"]),
                                 fear_tick=tick, fear_memory_id=str(episode.id),
                                 wildlife_warning={"x": victim.x, "y": victim.y, "expires": tick + 24})
        if observer.needs:
            observer.needs.safety = max(0, observer.needs.safety - 35)


def fear_at(citizen, tick):
    return max(0.0, float(citizen.metadata.get("fear", 0)) - max(0, tick - int(citizen.metadata.get("fear_tick", tick))) * 0.75)


def _visible(world, observer, victim):
    steps = max(abs(observer.x - victim.x), abs(observer.y - victim.y))
    for step in range(1, steps):
        x = round(observer.x + (victim.x - observer.x) * step / steps)
        y = round(observer.y + (victim.y - observer.y) * step / steps)
        tile = world.retrieve_tile(x, y)
        if tile is None or tile.terrain.value in {"MOUNTAIN"}:
            return False
        if any(home.completed and home.x == x and home.y == y and home.bed_capacity > 0 for home in world.structures.values()):
            return False
    return True


def memory_graph(world, citizen):
    """A small highlight graph; filtering never deletes the underlying memories."""
    highlights = []
    seen = set()
    for episode in reversed(world.episodes.get(str(citizen.id), [])):
        action = str(episode.details.get("action_type", episode.summary.split(" ")[0])).lower()
        significant = episode.episode_type == EpisodeType.DANGER or (
            episode.episode_type in {EpisodeType.DISCOVERY, EpisodeType.COMMUNICATION}
            and episode.importance >= 0.7
        ) or (
            episode.episode_type == EpisodeType.ACTION_RESULT
            and action in {"build", "craft"}
            and episode.details.get("succeeded") is True
        )
        if not significant:
            continue
        key = (episode.episode_type, episode.summary, episode.x, episode.y)
        if key in seen:
            continue
        seen.add(key)
        highlights.append(episode.model_dump(mode="json"))
        if len(highlights) == 12:
            break
    return list(reversed(highlights))
