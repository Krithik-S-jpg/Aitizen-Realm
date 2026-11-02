"""Nearby overland casualty retrieval, with no healing or remote pickup."""
from app.domain.models.navigation import MovementStatus


def retrieve(decisions, world, trip, members, tick):
    rescue = trip.get("rescue")
    if not rescue:
        patient = next((e for e in members if not e.active or e.needs.health <= 35), None)
        if patient is None:
            return False
        helper = next(e for e in members if e.id != patient.id)
        if not helper.active or helper.needs.health < 70 or helper.needs.energy < 40:
            return False
        interior = any(e.metadata.get(k) for e in members for k in ("dive_trip", "in_cave"))
        extraction = None
        if interior:
            from app.application.services.interior_rescue import start
            extraction = start(world, patient, helper)
            if extraction is None:
                return False
        elif any(e.metadata.get("aboard") for e in members):
            return False
        if helper.distance_squared_to(patient.x, patient.y) > helper.perception_radius**2:
            return False
        if decisions._threats(world, helper):
            return False
        rescue = trip["rescue"] = {"patient": str(patient.id), "helper": str(helper.id), "picked_up": False}
        if extraction:
            rescue.update(extraction)
            for e in members:
                e.metadata["rescue_controlled"] = True
        trip.update(phase="rescuing", reason="Retrieve injured companion to the departure point")
        for e in members:
            active = decisions._lifecycle.active(e.id)
            if active:
                decisions._lifecycle.fail(*active, tick, "Interrupted for casualty retrieval")
            plan = world.movement_plans.get(str(e.id))
            if plan:
                plan.status = MovementStatus.CANCELLED
    patient, helper = world.entities[rescue["patient"]], world.entities[rescue["helper"]]
    if not helper.active or helper.needs.energy < 20 or helper.needs.critical or decisions._threats(world, helper):
        patient.metadata.pop("carried_by", None)
        raise ValueError("Rescuer cannot safely continue; casualty left at current location")
    if rescue.get("mode") in {"cave", "water"}:
        from app.application.services.interior_rescue import advance
        if advance(world, rescue, patient, helper, tick):
            rescue["mode"] = "land"
            rescue["picked_up"] = True
        return True
    if rescue["picked_up"]:
        # The helper's ordinary land path advanced by one tile. Passenger follows
        # only after the physical pickup, not from an arbitrary remote location.
        patient.x, patient.y = helper.x, helper.y
        helper.needs.energy = max(0, helper.needs.energy-1)
    elif (helper.x, helper.y) == (patient.x, patient.y):
        rescue["picked_up"] = True
        patient.metadata["carried_by"] = str(helper.id)
        helper.metadata["carrying_casualty"] = str(patient.id)
    target = trip["origins"][str(helper.id)] if rescue["picked_up"] else [patient.x, patient.y]
    if rescue["picked_up"] and [helper.x, helper.y] == target:
        patient.metadata.pop("carried_by", None)
        helper.metadata.pop("carrying_casualty", None)
        rescue["delivered_tick"] = tick
        trip.update(phase="rescued", reason="Casualty retrieved; medical recovery still required")
        return True
    plan = world.movement_plans.get(str(helper.id))
    if not plan or plan.status != MovementStatus.MOVING or [plan.destination_x, plan.destination_y] != target:
        if not decisions._navigation._find_path(world, helper, *target):
            raise ValueError("No safe known overland casualty retrieval route")
        decisions._navigation.plan(helper.id, *target, tick)
    helper.metadata.update(state="move", last_decision_reason=trip["reason"])
    patient.metadata.update(state="rest", last_decision_reason="Waiting for companion's assistance")
    return True
