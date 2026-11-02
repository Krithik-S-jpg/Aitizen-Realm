# Changing Planet: freshwater milestone

New seeded worlds receive one connected drainage channel to existing water when
an outlet exists. Existing saves are not recarved. The channel uses elevation-aware
path costs; it is not a fluid or erosion simulation.

Each tick, seasonal baseline and rainfall intensity gradually change the water
level. Cached low banks adjoining freshwater flood and recede. Original terrain
is preserved, but flooded banks block walking and swimming shortcuts. Existing
movement steps revalidate passability. Autonomous citizens interrupt ordinary work
and sleep to evacuate across known flooded banks to dry ground, one step per tick.
They never cross open river/ocean tiles as an evacuation shortcut. If no known
escape exists, they wait without teleporting. Nearby awake citizens hear a
deduplicated warning with source/expiry and retain an important danger memory.

Build now includes a bridge: 16 wood, 4 stone, 28 work. Only a single freshwater
tile with opposing dry banks is eligible. Unfinished bridges do not open paths.
Completed crossings use walking, not swimming stamina. Safe daylight citizens
review adjacent known crossings at most once per 24 ticks, proposing a bridge when
the opposite known bank has no short land route. At most two unfinished bridges
are proposed globally. Normal settlement jobs, gathering, delivery and building
complete the project; planning creates neither materials nor finished structures.
Long-span bridges are not supported.

Hydrology is stored in world checkpoints. Live scene responses carry flood
coordinates so the renderer can show blue flooded banks without terrain reloads.
Bridge planks and rails are procedural, not new painted assets.

Tests: `python -m pytest tests/test_flood_response.py tests/test_hydrology.py tests/test_decisions.py tests/test_living_world.py`.
`client/tools/TestFloodWorld.gd` renders flood/bridge/citizen and recession frames;
screenshots are in `client/.agent-qa/flood-active.png` and `flood-receded.png`.
Live saved-world play-through, broader performance benchmarks, local rainfall footprints,
bridge deterioration and terrain-edit cache invalidation remain follow-up work.
