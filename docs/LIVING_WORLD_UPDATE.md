# Connected living-world update

## Implemented

- Citizens retain bounded decision checks and recent action outcomes for the inspector. Unavailable actions record a reason instead of silently disappearing.
- Cold citizens can pursue construction or materials instead of repeatedly selecting their current tile as safety. Community hunger influences farm priority.
- Repeated citizen travel leaves traffic metadata. Citizens can choose affordable road construction near known storage; completed roads remain traversable and reduce path cost.
- Wildlife aging and reproduction timing use the configured simulation day length. Citizen aging uses the same calendar boundary.
- Animal and building observation pages expose actual simulation records and camera focus. Population charts plot recorded samples, including citizens and wildlife.
- Economy resource totals include communal stockpiles as well as inventories. Moving citizens display carried materials from their inventory.
- World updates finish before completed-tick notifications are emitted. Failed updates do not emit a successful completion event.
- Static terrain is batched into a cached mesh. Resource and structure updates reuse that mesh; sparse ambient details reduce rendering work.

## Verification

- Backend suite: 141 tests passed.
- End-to-end resource test: tree to ground logs to gathering to storage to withdrawal to completed shelter, with material conservation checks.
- Autonomous survival acceptance requires a completed building, not only survival.
- Additional coverage: road selection/traversability, decision explanations, storage accounting, configurable lifecycle timing, and tick notification ordering/failure.
- Godot checks cover environmental motion/pause, distance-based gait, stationary gait, shorelines, world bounds, interaction ranges, and observation page layouts.
- Intel UHD OpenGL renderer fixture: approximately 25 FPS before optimization and 59.2 FPS after optimization, with draw calls reduced from 1,617 to 127. Final measurement uses 60 warm-up and 300 measured frames in a 64-by-64 world with 520 resources and 48 animals.

## Scope and remaining limits

This builds on existing needs, resource depletion, fire, farming, construction, animal behavior and animation systems. It is not a replacement of every animation asset or a claim of complete real-world physics.

The renderer fixture does not establish a steady 60 FPS for the full application under all populations, weather, networking and UI workloads. Observation pages show requested snapshots; camera focus is not continuous animal tracking. Markets and trade prices remain explicitly unavailable rather than fabricated.

Simulation update failure prevents a success notification but does not roll back already-applied mutations. Hosted Supabase authentication is a separate configuration issue and was not verified by these local tests.
