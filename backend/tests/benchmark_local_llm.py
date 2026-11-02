"""Isolated real inference timings; no world reads/writes. Run explicitly."""
import json
from time import perf_counter
from app.application.services.citizen_planner import propose

if __name__ == "__main__":
    rows = []
    for citizen in range(3):
        start = perf_counter()
        try:
            result = propose({"allowed_goals": ["REST", "EXPLORE"], "citizen": f"Benchmark {citizen}", "needs": {"energy": 90, "hunger": 10, "thirst": 10}}, "qwen2.5:1.5b")
            rows.append({"request": citizen+1, "seconds": perf_counter()-start, "valid": True, "goal": result["goal"]})
        except Exception as error:
            rows.append({"request": citizen+1, "seconds": perf_counter()-start, "valid": False, "error_type": type(error).__name__})
    print(json.dumps({"concurrency": 1, "model": "qwen2.5:1.5b", "requests": rows}, indent=2))
