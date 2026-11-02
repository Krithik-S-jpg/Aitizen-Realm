"""Varied local conversation grounded in personal state, not invented events."""


def discuss(service, world, speaker, listener, tick):
    knowledge = world.entity_knowledge[str(speaker.id)]
    other = world.entity_knowledge[str(listener.id)]
    topics = []
    ambition = speaker.metadata.get("ambition", {})
    if ambition:
        topics.append(("ambition", f"I want to {ambition['title'].lower()}. My progress is {ambition['progress']:g} of {ambition['target']:g}.",
                       "Let's compare what we learn when we next meet.", {}))
    lesson = speaker.metadata.get("last_learned_outcome", {})
    if lesson.get("failures", 0):
        topics.append(("learning", f"My last {lesson['action'].lower()} attempt failed: {lesson['reason']}. I'll try other work before returning."[:240],
                       "That is worth remembering. I'll check my own circumstances before trying.", {}))
    for key, record in knowledge.discoveries.items():
        if key not in other.discoveries or (record.data.get("inspected") and not other.discoveries[key].data.get("inspected")):
            topics.append((f"antiquity:{key}", f"I found {record.data['name']} near ({record.x}, {record.y}). {record.data.get('evidence', 'We should inspect it together.')}",
                           "Let's check the evidence ourselves before deciding what happened.", {"discoveries": [key]}))
    for category in ("resources", "structures"):
        for key, record in getattr(knowledge, category).items():
            if key not in getattr(other, category):
                kind = str(record.data.get("resource_type", record.data.get("structure_type", "supplies"))).lower()
                topics.append((f"discovery:{key}", f"I remember {kind} near ({record.x}, {record.y}). I last saw it at tick {record.last_seen_tick}; it may have changed.",
                               "I'll remember the location and check it myself.", {category: [key]}))
                break
    if speaker.needs:
        topics.append(("wellbeing", f"My energy is {speaker.needs.energy:.0f}/100. How are you managing?",
                       f"My energy is {listener.needs.energy:.0f}/100. I'll rest when I need to." if listener.needs else "I'm taking things one step at a time.", {}))
    reason = str(speaker.metadata.get("last_decision_reason", ""))
    if reason:
        topics.append(("plans", f"Right now I'm {speaker.metadata.get('state', 'idle').replace('_', ' ')}. {reason}"[:240],
                       "I understand. I'll look for useful work after taking care of my needs.", {}))
    topics.append(("exploration", f"I have learned about {len(knowledge.tiles)} tiles. There is still more to investigate beyond the places I know.",
                   f"I know {len(other.tiles)} tiles. Let's compare discoveries when we meet again.", {}))
    topics.append(("diet", f"I prefer {'plant food' if speaker.diet == 'vegetarian' else 'both plant food and meat'}. What about you?",
                   "I prefer plant food." if listener.diet == "vegetarian" else "I eat both, depending on what is available.", {}))
    recent = speaker.metadata.setdefault("conversation_topics", {})
    key, text, answer, shared = min(topics, key=lambda topic: recent.get(f"{listener.id}:{topic[0]}", -10000))
    stamp = f"{listener.id}:{key}"
    if tick - recent.get(stamp, -10000) < 120:
        return
    service.send(speaker.id, listener.id, text[:240], tick, shared)
    service.send(listener.id, speaker.id, answer[:240], tick)
    recent[stamp] = tick
    if len(recent) > 80:
        del recent[min(recent, key=recent.get)]
