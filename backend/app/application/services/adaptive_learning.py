"""Bounded, checkpoint-safe learning from real outcomes, never model claims."""
import json


def signature(action, target):
    return action + ':' + json.dumps(target, sort_keys=True, default=str)


def record_outcome(entity, action, tick, succeeded):
    lessons = entity.metadata.setdefault("action_lessons", {})
    key = signature(action.action_type.value, action.target)
    previous = lessons.get(key, {})
    failures = 0 if succeeded else min(8, previous.get("failures", 0) + 1)
    lessons[key] = {"action": action.action_type.value, "tick": tick,
                    "failures": failures, "retry_after": tick + min(96, 8 * failures),
                    "succeeded": succeeded, "reason": action.failure_reason or "Completed",
                    "target": dict(action.target)}
    if len(lessons) > 48:
        del lessons[min(lessons, key=lambda item: lessons[item]["tick"])]
    entity.metadata["last_learned_outcome"] = dict(lessons[key])


def retry_blocked(entity, action, target, tick):
    lesson = entity.metadata.get("action_lessons", {}).get(signature(action, target), {})
    return lesson.get("failures", 0) > 0 and tick < lesson.get("retry_after", 0)


def remember_danger(entity, warning, source_id):
    if not warning.get("event_id"):
        return
    memories = entity.metadata.setdefault("learned_dangers", {})
    key = warning["event_id"]
    if key not in memories:
        memories[key] = {**warning, "source_id": str(source_id)}
    if len(memories) > 16:
        del memories[min(memories, key=lambda item: memories[item].get("observed_tick", 0))]


def danger_cost(entity, x, y, tick):
    # Old evidence becomes less certain; hearsay cannot renew its observation time.
    cost = 0.0
    for warning in entity.metadata.get("learned_dangers", {}).values():
        age = max(0, tick - warning.get("observed_tick", 0))
        if age > 960:
            continue
        distance = (x-warning["x"])**2 + (y-warning["y"])**2
        cost = max(cost, max(0, 36-distance) * .35 * (1-age/960))
    return cost


def update_ambition(world, entity, tick):
    knowledge = world.entity_knowledge[str(entity.id)]
    ambition = entity.metadata.get("ambition")
    if not ambition:
        # Stable identity-based preference, not a fixed profession.
        kind = ("explore", "build", "gather")[entity.id.int % 3]
        ambition = {"kind": kind, "title": {"explore": "Map 40 new tiles", "build": "Improve my building skill", "gather": "Become a skilled forager"}[kind],
                    "started_tick": tick, "baseline": len(knowledge.tiles) if kind == "explore" else entity.skills.get("building" if kind == "build" else "foraging", 0),
                    "target": 40 if kind == "explore" else 10, "progress": 0, "status": "active"}
        entity.metadata["ambition"] = ambition
    value = len(knowledge.tiles) if ambition["kind"] == "explore" else entity.skills.get("building" if ambition["kind"] == "build" else "foraging", 0)
    ambition["progress"] = min(ambition["target"], max(0, value-ambition["baseline"]))
    if ambition["progress"] >= ambition["target"] and ambition["status"] == "active":
        ambition.update(status="completed", completed_tick=tick)
    return ambition


def safe_to_pursue(entity):
    n = entity.needs
    return bool(n and n.health > 75 and n.hunger < 40 and n.thirst < 40 and n.energy > 70 and n.safety > 70)


def verify_reports(world, observer, visible_resources, tick):
    """Reward confirmed resource tips once; absence isn't proof of dishonesty."""
    visible = {str(record["id"]): record for record in visible_resources}
    reports = observer.metadata.get("resource_reports", {})
    for key, report in list(reports.items()):
        if tick - report["tick"] > 480:
            del reports[key]
            continue
        resource = visible.get(report["resource_id"])
        if not resource or (resource["x"], resource["y"]) != (report["x"], report["y"]):
            continue
        bond = world.social_bonds.get(f"{observer.id}:{report['source_id']}")
        if bond:
            bond.trust = min(1, bond.trust + .05)
        observer.metadata["last_verified_report"] = {**report, "verified_tick": tick, "outcome": "Personally confirmed resource location"}
        verified = observer.metadata.setdefault("verified_reports", {})
        verified[key] = tick
        while len(verified) > 48:
            del verified[next(iter(verified))]
        del reports[key]
