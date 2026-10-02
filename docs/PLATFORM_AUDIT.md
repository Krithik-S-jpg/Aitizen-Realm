# Platform foundation audit

Date: 2026-09-24. Scope: current local working tree, including pre-existing uncommitted work. This is a source and test-baseline audit, not certification of every feature or a completed implementation of the supplied 30-step specification. No working systems were removed or replaced.

## Existing architecture to retain

- Python/FastAPI routes delegate to application services and Pydantic domain models. Repository, engine, event bus and scheduler interfaces already exist.
- `backend/app/infrastructure/api/dependencies.py` wires one shared in-memory world and runs resources, navigation, needs, wildlife, decisions, memory, society and analytics each tick.
- Godot consumes REST state and simulation WebSocket events. `WorldRenderer.gd` is a custom Node2D renderer, not a TileMap API. Preserve its public coordinate and bounds contracts.
- `World` already contains chunks, resources, inventories, structures, entities, knowledge, movement plans, actions, goals, episodes, messages, bonds and groups. Extend these instead of introducing duplicate world/citizen models.

## Evidence-based status

| Area | Status | Evidence and qualification |
| --- | --- | --- |
| Engine / API | Implemented baseline | Engine lifecycle, stepping, scheduling and API tests pass. Full failure recovery and multi-process ownership are not established. |
| Terrain / streaming | Implemented baseline | Seeded generation, multiple biomes and negative-coordinate chunks have tests. Full simulation replay determinism is not proven by terrain tests. |
| Resources / construction | Partial end-to-end | Reservation, depletion, ground timber, inventories, crafting, shared storage and construction services exist with focused tests. The survival acceptance test no longer asserts BUILD completion despite its name. |
| Citizens / utility | Partial | Needs, private perception, utility decisions, navigation, goals and memory exist. This is the basis for AURELIA, not a reason to build a second decision engine. Full identity, family, ownership and long-term planning are not established. |
| Wildlife | Partial | Species configuration, habitat checks, patrol, predation and lifecycle tests exist. Visual motion quality and ecology over long runs remain acceptance work. |
| Society | Partial | Social bonds, professions and groups exist. These are not evidence of a working economy, law, culture or civilization model. |
| Research | Partial | Metrics, experiment records and event export exist in memory. Durable experiments, replay and restart recovery are missing. |
| Database | Missing | Repository stores a Python World reference. No PostgreSQL adapter or migrations found; serialization is not durable storage. |
| Redis / deployment | Missing in inspected source inventory | No Redis integration, Docker/compose or CI definitions found. Do not add Redis as a second authority. |
| Godot UI | Partial / defects found | Two navigation listeners could toggle Build twice. Event bursts could freeze the UI. Both repaired in this pass. |
| Tests / performance | Partial assurance | Baseline: 125 backend tests passed. Focused Godot scripts exist. No integrated graphical 60 FPS guarantee or full visual acceptance was performed. |

## Confirmed defects and risks

1. **Fixed:** notification trimming called deferred `queue_free()` inside a child-count loop. The count never decreased synchronously. Detach before freeing; bind tweens to cards and cap duplicate tracking. Added a 20-event burst regression.
2. **Fixed:** event cursor pagination selected the last page of matching events, skipping earlier retained records. Return the earliest next page; added multi-page regression coverage.
3. **Fixed:** Main and UIManager both handled Build/Citizens/Research navigation. UIManager now owns ordinary pages; Main owns environment settings.
4. **Open:** clock customization and biological time are inconsistent. Audit fixed 24-tick assumptions and midnight-to-six sleeping against configurable night boundaries before expanding the calendar.
5. **Open:** event history and metrics have no explicit run identity/reset boundary. Completed structures are rescanned and bounded dedup eviction can reintroduce old completion events.
6. **Open:** tick mutation and broadcasts subscribe to the same concurrently dispatched event. Registration order is not a transaction guarantee. Establish an explicit advance-then-publish boundary and test failed ticks.
7. **Open:** in-memory repository locks protect reference access, not all mutation of the returned world. Durable checkpoints need a simulation-owned coherent snapshot boundary.
8. **Open:** `test_agent_survives_and_builds_from_world_resources` does not currently assert successful construction. Restore a genuine resource-to-building acceptance contract and fix its cause; do not weaken survival assertions to declare success.
9. **Open:** settings requests, disconnects, world replacement, asset clipping, interpolation and long-running population cost require integrated tests.

## Duplication and obsolete-code candidates

- Navigation ownership was duplicated and is now narrowed.
- Separate `advance_world_resources`, `advance_world_entities` and `capture_world_metrics` helpers coexist with the combined tick function. Confirm callers before consolidation.
- `DebugWorldRenderer.gd`, legacy settings controls and preview scripts require reference checks before deletion. They are candidates, not proven obsolete; retained unchanged.
- Existing domain/application services must remain the extension points. Do not create parallel AURELIA, citizen, calendar or resource engines.

## Implementation sequence and acceptance gates

1. **Reliability:** coherent tick publication, run-scoped events, configured sleep/time, lossless commands and restored survival-to-construction test. Test restart/reset/disconnect and UI navigation, not only isolated methods.
2. **Persistence:** versioned checkpoint envelope containing world, tick, calendar/config, schema version and run identity. PostgreSQL migrations for implemented run/checkpoint/experiment/event/metric domains with constraints/indexes. Add repository adapters through dependency injection, keep active state in memory, test restore equivalence and failed-write recovery. Supabase credentials stay server-side; do not persist every frame/tick by default.
3. **Explainability:** expose existing utility candidates, scores, unmet prerequisites, chosen goal and consequences. UI must use real values and distinguish unknown/stale observations.
4. **Ecology and citizen continuity:** habitat-aware behavior, coherent biological clocks, persistent tasks, material conservation, family/property domains only when their rules and tests exist.
5. **Research and operations:** reproducible experiments and replay checks, migrations, Docker/CI, measured simulation and render budgets. Add Redis only for a demonstrated coordination need with one simulation owner.
6. **Later social systems:** farming/economy/discovery/culture backed by actual production, exchange and evidence. Optional LLM strategic reasoning must not replace ordinary deterministic actions.

## Verification limitations

The baseline backend suite passes with two dependency deprecation warnings. The new event pagination test and headless Godot notification burst test pass. Godot reports an environment root-certificate-store warning. Visual quality, hosted database connectivity, restart persistence, 100x simulation and real-window 60 FPS have not been validated or claimed. The broader transformation remains outstanding.
