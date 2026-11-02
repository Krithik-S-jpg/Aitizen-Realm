# Acceptance findings — 2026-10-21

This is not a completion certificate.

## Fix
Household supply collection now routes beside completed shelters instead of
attempting to enter the blocked building tile.

## Rendering: failed performance target
Existing dense-world renderer fixture: 64x64 terrain, 520 resources, 48 entities,
rain, 1152x648 window, Intel UHD, Vulkan Forward+.
300 frames after warmup: 45.3 FPS average, 20.48 ms median, 37.10 ms p95,
45.32 ms worst; 673 draw calls in the final sample. Target >=55 FPS not met.
This is a synthetic world, not a full live saved-game acceptance run. Other test
processes may have overlapped; use an otherwise idle machine for controlled comparisons.

## Population: scaling bottleneck measured
Run `python -m tests.benchmark_world --citizens 50 100 250 --ticks 10` from backend.
Fixture covers navigation, needs and utility decisions, not all production tick
services, and does not call the LLM. The 100-tick run was interrupted after an
extended wait; only the completed 10-tick run is reported here.

| Citizens | Median update | Maximum update |
|---|---:|---:|
| 50 | 64.1 ms | 320.5 ms |
| 100 | 164.8 ms | 708.3 ms |
| 250 | 1265.2 ms | 4056.3 ms |

Small samples are diagnostics, not stable capacity promises. The 250-citizen
fixture cannot maintain a one-second update budget.

## Reconnection
Added `TestLiveReconnect.gd` and `test_godot_restart.py` to exercise the actual
client across an isolated backend restart, with test-only recovery storage.
Initial attempts failed to establish the first client connection within 35 seconds;
do not treat end-to-end reconnection as verified. Earlier policy and backend-only
restart tests are distinct and do not establish full-client acceptance.

## Still open
Remaining appearance/age artwork and hunting cleanup; broader child supervision
and supply sourcing; profiling/optimization for population and Forward+ rendering;
successful end-to-end reconnect and full saved-world visual checks.
