# Underwater expeditions

## Use in the app

Restart the backend and Godot client after updating. New worlds initialize habitats
immediately; loading an older checkpoint adds missing marine data without replacing
existing citizens, terrain or inventory. Save again to persist the upgrade.

Surface / Underwater changes only the observation layer. It does not send a citizen
into the water. These controls hide while full-screen pages are open.

In **Citizens**, select a citizen. The right inspector scrolls to expedition controls:

1. For a shore dive, stand beside known shallow water with at least 70 energy and
   60 health. Choose **Dive from shore / anchored boat**.
2. For an expedition, carry 20 wood and 8 fiber. Select **Build boat**, then apply.
3. Stand beside water; apply **Launch**, then **Board**. A launched boat is a world
   object with one occupant and 100 units of cargo space, not just a sprite.
4. Enter known water X/Y coordinates and apply **Row**. The boat anchors on arrival.
   **Anchor** can stop a voyage early. Rowing consumes stamina.
5. Dive from the anchored boat. The diver reserves oxygen/stamina to retrace their
   route. **Return diver to safety** recalls them early without teleporting.
6. On return, **Store dive cargo** transfers underwater finds into the anchored boat.
7. Row to a shoreline, anchor, and **Disembark**. **Unload cargo** transfers as much
   as fits back to the citizen when aboard or beside their boat.
8. **Follow citizen / diver** selects the citizen for camera tracking and chooses
   the appropriate observation layer at selection time.

## Simulation and visuals

- Seeded sand, rock, kelp and reef habitats with depth and rare wreck/cave landmarks.
- Marine wildlife capped at 160 per world; spawned only in water, crabs restricted
  to shallow habitat. Fish use local school peers, seek food and flee; sharks hunt
  fish; jellyfish use a changing current direction. Updates happen on simulation
  ticks, with client movement interpolation independent of AI updates.
- Finite shells, pearls, seaweed, minerals and salvage. Collecting requires visiting
  the tile, available inventory capacity, an outbound dive and a per-trip limit.
- Explored sites persist per citizen and appear on the minimap. Important finds
  create one discovery memory; routine revisits do not spam the memory graph.
- Blue depth shading, light shafts, shimmer and particles; clustered kelp, coral,
  rocks, wrecks and caves. Marine art is transparent and has species-specific frames.
- All eight aquatic appearances have swimming plus separate descent, gathering and
  surfacing source poses. Existing citizen identities are retained.
- Inspector exposes oxygen, stamina (energy), depth, return location, discoveries
  and boat cargo. These values come from authoritative state.

## Explicit limits

This is a bounded breath-hold expedition system: at most three tiles outward, then
return. Shore dives cannot enter ocean tiles; anchored-boat dives can. Caves and
wrecks are discoverable landmarks, not separately navigable interiors. Marine AI
uses local grid decisions rather than fluid dynamics; marine reproduction and
long-term aging are not included. Shark artwork has one pose, other new marine
animals four; dive actions have two poses per action, not 24 distinct frames.

The existing emergency behavior surfaces a citizen if a route becomes blocked;
it does not implement a rescue crew or drowning simulation. Boat cargo is stored
in the ordinary inventory model. There are no new Supabase tables: the complete
world checkpoint contains the new fields, resources, animals, boat and inventories.
Live hosted Supabase writes were not exercised by the automated tests.

## Verification

Backend: `python -m pytest` in backend. Targeted suite:
`python -m pytest tests/test_diving.py tests/test_water_travel.py tests/test_marine_expeditions.py`.

Coverage includes oxygen return reserves, tick idempotency, shore/ocean restrictions,
boat commands through the API, craft/launch/board/row/dive/collect/store/disembark,
world JSON round trips, finite capacity, important discovery deduplication, predator
hunting, fish fleeing and water-only movement.

Godot: run `res://tools/TestAquatic.gd`, `TestDepthControls.gd`, and
`TestExpeditionUI.gd`. The graphical tests save screenshots under client/.agent-qa.
Asset prompts and provenance are in client/assets/pixel_art/aquatic/README.md.
