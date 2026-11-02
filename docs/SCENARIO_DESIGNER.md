# Scenario designer

Open **World overview → World editor → Open scenario designer**. Pause the
simulation for validation, saving, starting, stopping or deleting designs.
Resume the simulation to advance the scenario. The Live progress tab refreshes
every three seconds while open; the backend continues when it is closed.

## Authoring

Name your scenario and write a briefing. Add objectives with unique IDs:

- `elapsed`: ticks since Start.
- `population`: active living citizens, not animals.
- `structures`: completed, non-destroyed structures; blank subject means all,
  otherwise use the uppercase type, such as SHELTER or BRIDGE.
- `inventory`: a lowercase item name, such as wood; current citizen inventories
  plus completed building stockpiles. Not lifetime gathering totals.
- `explored`: unique tiles currently known by living active citizens.

All objectives must be met **at the same time**. Existing world progress counts.
Add an elapsed objective if citizens must maintain other goals until a set time.
Zero deadline disables the time limit; zero minimum population disables that
failure condition. Minimum-population failure takes priority over success.
At the deadline, met objectives win; otherwise the scenario fails.

## Timeline

Add messages, finite resource brushes or local weather brushes. Tick offsets are
relative to Start. An optional objective ID delays execution until that objective
is met. Equal-time events execute in document order. Events run once, including
after checkpoint restore. Tick-zero events run immediately when Start is pressed.

Coordinates refer to the current world. Resource events preserve occupied and
protected tiles. Weather supports rain, snow or clear, radius 0–2, 48-tick duration,
and the existing four-active-patch limit. Blocked events explicitly skip or fail
the scenario according to their policy; they do not silently retry or overwrite.
Events execute after simulation updates. Remaining events are cancelled when
the scenario completes, fails or is stopped. Applied world changes remain.

## Library and persistence

Save design before Start saved. New/Duplicate creates another library entry;
Load replaces the unsaved form. Delete asks for confirmation. A running scenario
uses an immutable copy, so edits to the saved design affect the next run only.
Revision checks reject stale overwrites. One run is active per world.

Save world persists the library, active run, event receipts, progress and history.
Start does **not** reset terrain, citizens or inventories. For repeatable trials,
save the desired starting world and restore it before starting another run.
The latest run is retained; export results before replacing it with a new run.

Import/Export exchanges schema-version-1 JSON designs, not world snapshots.
Imports require server validation before entering the form. Export results writes
the latest observed run definition, progress and timestamped log as JSON.
Limits: 20 designs/world, 32 objectives/design, 64 events/design, last 256 log entries,
256 KB file import. No executable scripts, arbitrary commands or LLM-generated
world mutations are accepted.

## Verification and scope

Tests cover objective gates, deadlines, population failure, stale revisions,
protected placement, duplicate-tick safety, serialization and real checkpoint
HTTP routes backed by isolated compressed storage. Godot tests exercise form
roundtrips and render the UI. Hosted Supabase and a prolonged player-driven run
still require acceptance testing. This is a goal/timeline designer, not a visual
branching campaign editor or arbitrary behavior scripting language.
