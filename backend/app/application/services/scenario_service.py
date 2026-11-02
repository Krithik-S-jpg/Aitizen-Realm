"""Deterministic scenario execution, persisted alongside the authoritative world."""
from uuid import uuid4
from copy import deepcopy
from app.domain.models.scenario import ScenarioDefinition
from app.application.services import editor_tools


def validate_world(world, definition):
    for event in definition.events:
        if event.kind != "message" and not (event.radius <= event.x < world.width-event.radius and event.radius <= event.y < world.height-event.radius):
            raise ValueError(f"Event {event.id} brush crosses world bounds.")


def save(world, definition, scenario_id="", revision=0):
    validate_world(world, definition)
    if scenario_id:
        old = world.scenarios.get(scenario_id)
        if old is None or old["revision"] != revision:
            raise ValueError("Scenario changed or was removed. Refresh before saving.")
    elif len(world.scenarios) >= 20:
        raise ValueError("This world already has 20 scenarios.")
    scenario_id = scenario_id or str(uuid4())
    world.scenarios[scenario_id] = {"revision": revision + 1, "definition": definition.model_dump()}
    return scenario_id


def metric(world, goal, elapsed):
    citizens = [e for e in world.entities.values() if e.kind.value == "AGENT" and e.active and (e.needs is None or e.needs.health > 0) and not e.metadata.get("dead", False)]
    if goal.metric == "elapsed":
        return elapsed
    if goal.metric == "population":
        return len(citizens)
    if goal.metric == "structures":
        return sum(s.completed and s.condition > 0 and (not goal.subject or s.structure_type.value == goal.subject) for s in world.structures.values())
    if goal.metric == "inventory":
        inventories = [world.inventories[str(e.id)] for e in citizens if str(e.id) in world.inventories]
        inventories += [s.stockpile for s in world.structures.values() if s.completed and s.condition > 0]
        return sum(inv.items.get(goal.subject.lower(), 0) for inv in inventories)
    tiles = set()
    for e in citizens:
        knowledge = world.entity_knowledge.get(str(e.id))
        if knowledge:
            tiles.update(knowledge.tiles)
    return len(tiles)


def log(run, tick, message):
    run["history"].append({"tick": tick, "message": message})
    del run["history"][:-256]


def start(world, scenario_id, tick):
    if world.scenario_run.get("status") == "running":
        raise ValueError("Stop the current scenario first.")
    if scenario_id not in world.scenarios:
        raise ValueError("Save or select a scenario first.")
    definition = ScenarioDefinition.model_validate(world.scenarios[scenario_id]["definition"])
    validate_world(world, definition)
    world.scenario_run = {"id": str(uuid4()), "scenario_id": scenario_id, "definition": definition.model_dump(),
                          "status": "running", "started_tick": tick, "last_tick": tick-1,
                          "elapsed": 0, "events": {}, "objectives": {}, "history": []}
    log(world.scenario_run, tick, "Started on the current world. Existing progress counts toward goals.")
    advance(world, tick)


def advance(world, tick):
    run = world.scenario_run
    if run.get("status") != "running" or tick <= run["last_tick"]:
        return
    run["last_tick"] = tick
    elapsed = tick-run["started_tick"]
    run["elapsed"] = elapsed
    definition = ScenarioDefinition.model_validate(run["definition"])
    # Goals are current-state conditions, not permanently latched achievements.
    for goal in definition.objectives:
        value = metric(world, goal, elapsed)
        run["objectives"][goal.id] = {"label": goal.label, "value": value, "target": goal.target, "met": value >= goal.target}
    population_goal = definition.objectives[0].model_copy(update={"metric": "population"})
    if metric(world, population_goal, elapsed) < definition.minimum_population:
        run["status"] = "failed"
        log(run, tick, "Failed: population fell below the required minimum.")
        return
    for event in sorted(definition.events, key=lambda event: event.at_tick):
        if event.id in run["events"] or elapsed < event.at_tick:
            continue
        if event.after_objective and not run["objectives"][event.after_objective]["met"]:
            continue
        try:
            if event.kind == "message":
                detail = event.message or event.id
            else:
                preview = editor_tools.preview(world, event.x, event.y, event.radius, event.kind, event.choice, tick)
                if not preview["can_apply"]:
                    raise ValueError("; ".join(preview["blocked"]))
                # Scenario mutations are not editor undo operations.
                history = deepcopy(world.editor_history)
                editor_tools.apply(world, event.x, event.y, event.radius, event.kind, event.choice, tick, preview["token"])
                world.editor_history = history
                detail = preview["description"]
            run["events"][event.id] = "applied"
            log(run, tick, f"{event.id}: {detail}")
        except ValueError as error:
            run["events"][event.id] = "blocked"
            log(run, tick, f"{event.id} blocked: {error}")
            if event.on_blocked == "fail":
                run["status"] = "failed"
                return
    if all(goal["met"] for goal in run["objectives"].values()):
        run["status"] = "completed"
        log(run, tick, "Completed: all objective conditions met together. Remaining events cancelled.")
    elif definition.deadline and elapsed >= definition.deadline:
        run["status"] = "failed"
        log(run, tick, "Failed: deadline reached before all objectives were met.")
