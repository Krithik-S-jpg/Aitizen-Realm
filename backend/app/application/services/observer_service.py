"""Read-only, bounded monitoring projection. Never exports credentials or raw metadata."""
from datetime import datetime, timezone
from app.domain.models.calendar import calendar_at_tick


def snapshot(world, tick, state, analytics):
    if world is None:
        return {"schema": 1, "captured_at": datetime.now(timezone.utc).isoformat(), "state": "NO_WORLD", "tick": tick, "citizens": [], "alerts": [], "metrics": [], "world": None}
    citizens = []
    for entity in world.entities.values():
        if entity.kind.value != "AGENT":
            continue
        key = str(entity.id)
        goal = world.goals.get(world.active_goals.get(key, ""))
        action = world.actions.get(world.active_actions.get(key, ""))
        citizens.append({"id": key, "name": entity.name, "active": entity.active,
            "x": entity.x, "y": entity.y, "avatar": entity.avatar_id.value,
            "ai_mode": str(entity.metadata.get("ai_mode", "utility")),
            "needs": entity.needs.model_dump() if entity.needs else {},
            "action": action.action_type.value if action else str(entity.metadata.get("state", "idle")),
            "reason": goal.reason if goal else "No active goal recorded",
            "inventory": world.inventories[key].items if key in world.inventories else {},
            "memories": [{"tick": m.tick, "summary": m.summary, "kind": m.episode_type.value, "x": m.x, "y": m.y} for m in world.episodes.get(key, []) if m.importance >= .6][-8:]})
    messages = list(world.messages)[-80:]
    if messages and isinstance(messages[0], str):
        messages = [world.messages[key] for key in messages]
    events = [{"id": str(e.id), "tick": e.tick, "severity": e.severity.value, "title": e.title, "summary": e.summary, "x": e.x, "y": e.y} for e in analytics.all_events()[-100:]]
    for citizen in citizens:
        needs = citizen["needs"]
        risks = []
        if citizen["active"]:
            if needs.get("health", 100) <= 25:
                risks.append("critical health")
            if needs.get("hunger", 0) >= 80:
                risks.append("severe hunger")
            if needs.get("thirst", 0) >= 80:
                risks.append("severe thirst")
        if risks:
            events.append({"id": "needs:"+citizen["id"], "tick": tick, "severity": "DANGER", "title": citizen["name"]+" needs help", "summary": ", ".join(risks), "x": citizen["x"], "y": citizen["y"]})
    run = world.scenario_run
    return {"schema": 1, "captured_at": datetime.now(timezone.utc).isoformat(), "state": state, "tick": tick,
        "world": {"seed": world.seed, "width": world.width, "height": world.height},
        "calendar": calendar_at_tick(tick).model_dump(mode="json"), "citizens": citizens[:500],
        "population": sum(c["active"] and c["needs"].get("health", 100) > 0 for c in citizens),
        "supplies": analytics._inventory_totals(world), "buildings": [{"id": str(s.id), "type": s.structure_type.value, "x": s.x, "y": s.y, "progress": min(1, s.progress/s.work_required), "condition": s.condition} for s in world.structures.values()][:500],
        "scenario": {"name": run.get("definition", {}).get("name"), "status": run.get("status"), "elapsed": run.get("elapsed"), "objectives": run.get("objectives", {}), "history": run.get("history", [])[-20:]},
        "alerts": events[-120:], "metrics": [m.model_dump(mode="json") for m in analytics.history(limit=120)],
        "conversations": [{"id": str(m.id), "sender": str(m.sender_id), "recipient": str(m.recipient_id), "tick": m.tick, "content": m.content} for m in messages],
        "truncated": len(citizens) > 500 or len(world.structures) > 500}
