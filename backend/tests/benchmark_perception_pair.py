"""Paired diagnostic with stable citizen IDs and the old duplicate-pass behavior."""
from statistics import median
from time import perf_counter
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5
import json
from app.domain.models.entity import Entity, EntityKind
from app.application.services.decision_service import DecisionService
from tests.test_decisions import _systems


def sample(duplicate):
    entities, decisions, _ = _systems()
    def stable_entity(**fields):
        return Entity(id=uuid5(NAMESPACE_URL, fields["name"]), **fields)
    with patch("app.application.services.entity_service.Entity", side_effect=stable_entity):
        for i in range(100):
            actor = entities.create(EntityKind.AGENT, f"benchmark-{i}", 2+i%12, 2+(i//12)%12, tags={"autonomous"})
            actor.metadata["age_days"] = 30*365
    original = decisions.decide
    if duplicate:
        decisions.decide = lambda entity_id, tick, **kwargs: original(entity_id, tick)
    samples = []
    for tick in range(1, 6):
        start = perf_counter()
        decisions._navigation.advance_all(tick)
        decisions._needs.advance_all(tick)
        decisions.advance_all(tick)
        samples.append((perf_counter()-start)*1000)
    return {"duplicate_observation": duplicate, "median_ms": median(samples), "samples_ms": samples}


if __name__ == "__main__":
    print(json.dumps([sample(mode) for mode in (True, False, False, True)], indent=2))
