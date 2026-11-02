"""Repeatable small navigation benchmark; never touches the running world."""
from time import perf_counter
from statistics import median
from tests.test_community_routines import community


def measure(remembered):
    world, actor, _, decisions, _ = community()
    actor.perception_radius = 12
    actor.x, actor.y = 1, 5
    decisions._perception.observe(actor.id, 300)
    actor.metadata["decision_tick"] = 300
    if remembered:
        actor.metadata["learned_dangers"] = {str(i): {"x": 6, "y": 5, "observed_tick": i} for i in range(16)}
    times = []
    for _ in range(50):
        start = perf_counter()
        decisions._navigation._find_path(world, actor, 12, 5)
        times.append((perf_counter()-start)*1000)
    return median(times)


if __name__ == "__main__":
    print(f"16x16 navigation median, 50 routes: no memories {measure(False):.3f}ms; 16 danger memories {measure(True):.3f}ms")
