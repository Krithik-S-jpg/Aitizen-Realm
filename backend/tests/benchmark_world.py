"""Read-only synthetic benchmark: python -m tests.benchmark_world.

No live repository or model requests. Tick numbers cover the decision fixture's
navigation, needs and decisions, not the full production tick or GPU rendering.
"""
import json
import argparse
from statistics import median
from time import perf_counter
from app.application.services.world_generator import WorldGenerator
from app.domain.models.entity import EntityKind
from tests.test_decisions import _systems


def run(counts=(1, 10, 50), ticks=20):
    rows = []
    for size in (32, 64, 128):
        start = perf_counter()
        world = WorldGenerator.generate_terrain_world(size, size, seed=847291)
        generation = perf_counter() - start
        start = perf_counter()
        payload = world.model_dump_json().encode()
        rows.append(dict(kind="world", size=size, generation_s=generation,
                         serialization_s=perf_counter()-start, snapshot_bytes=len(payload)))
    for count in counts:
        entities, decisions, _ = _systems()
        for i in range(count):
            entities.create(EntityKind.AGENT, f"Benchmark {i}", 2+i%12, 2+(i//12)%12, tags={"autonomous"})
        samples = []
        for tick in range(1, ticks+1):
            start = perf_counter()
            decisions._navigation.advance_all(tick)
            decisions._needs.advance_all(tick)
            decisions.advance_all(tick)
            samples.append((perf_counter()-start)*1000)
        rows.append(dict(kind="utility_fixture", citizens=count, ticks=ticks, median_ms=median(samples), p95_ms=sorted(samples)[min(len(samples)-1, int(len(samples)*.95))], max_ms=max(samples)))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--citizens", nargs="+", type=int, default=[1, 10, 50])
    parser.add_argument("--ticks", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.ticks <= 1000 or any(n < 1 or n > 500 for n in args.citizens):
        parser.error("Use 1–500 citizens and 1–1000 ticks")
    run(args.citizens, args.ticks)
