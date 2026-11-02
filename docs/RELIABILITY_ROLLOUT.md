# Reliability rollout

## Local recovery (initial implementation)

Opt in using `LOCAL_RECOVERY_ENABLED=true` in the backend environment. Restart
the backend for configuration changes. The default is disabled while acceptance
testing is pending. `LOCAL_RECOVERY_INTERVAL_TICKS` defaults to 300; this measures
simulation ticks, not wall-clock seconds.

Snapshots are written to `backend/.local-state/recovery.json.gz` by default.
`LOCAL_RECOVERY_PATH` can point to persistent local storage. Run only one backend
worker against this file. Do not share the path between independent worlds or
processes. Keep this directory on a persistent disk when hosting.

At a completed simulation-update boundary the world, calendar and clock are
serialized, checksummed and atomically replaced. One previous valid generation
is retained. Startup restores the newest valid generation **paused**; corrupt
generations fall back to the previous one. If neither is valid, startup fails
without replacing them. The simulation state endpoint exposes recovery status.

This is not a cloud backup or a complete research archive. Analytics history,
pending model requests and scheduled jobs are not captured. Changes since the
last checkpoint can be lost, including changes made while paused. Graceful
shutdown capture and in-game recovery indicators are not implemented yet.

## Remaining acceptance work

- Restart lifecycle integration and cloud overwrite/load regression tests.
- Caregiving, teaching, carrying and age-specific animations; hunting cleanup.
- Supervised children, water/food delivery, elder workloads and family preferences.
- Population benchmarks and concurrency limits across all model consumers.
- Separate generation, tick, rendering and network measurements.
- Offline/reconnecting interface and restart recovery in a running Godot client.

Births remain experimental. Do not interpret unit-test success as full saved-world
or live-animation acceptance.

## Follow-up implementation (2026-10-17)

- Family care consumes actual carried water, respects vegetarian children, assigns
  an available distant guardian, and does not reduce skills during lessons.
- Infant/toddler supervision can interrupt optional work; elders prefer earlier
  rest at low energy. Comprehensive safe child movement and fetching household
  supplies remain unfinished.
- Animated care/teaching indicators are connected to authoritative care events.
  These are effects, not new dedicated body-animation frames.
- World fetch failures schedule read-only reconciliation with 2–30 second backoff.
  World-creation POSTs are never replayed by this reconnect timer. Reload no longer
  prematurely displays online status. Full backend-restart acceptance remains open.
- Six family tests passed. Run `python -m tests.benchmark_world` from backend for
  isolated deterministic benchmarks (no live world or model calls).

One local benchmark: 32/64/128 terrain generation 0.075/0.248/0.850 seconds;
snapshot sizes 287786/1167510/5041744 bytes; serialization 3/13/55 ms.
Utility fixture navigation/needs/decisions at 1/10/50 citizens: median
0.65/7.67/50.70 ms, maximum 22.88/40.51/264.98 ms over 20 updates.
These are single-run diagnostics, not production full-tick, network transfer,
LLM throughput or rendering measurements. Dedicated carry/work artwork,
hunting cleanup and live saved-world validation remain outstanding.
