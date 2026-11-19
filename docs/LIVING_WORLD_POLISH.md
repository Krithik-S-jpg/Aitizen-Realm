# Living-world polish — 19 November 2026

## Changes
- Citizen tile-sharing offsets ease toward deterministic positions; following uses the same position. Stationary actions ease out the final movement segment; travel stride remains distance driven. This is visual separation, not a physics collision system.
- Occupied homes display night window light, cold-weather smoke and dry-day linen movement. Small ornamental borders and approaches to adjacent completed roads are cached. These are decorations, not new food or fuel production.
- Existing species thirst, grazing, danger and grouping behavior is retained. Feeding sprites no longer bob off the ground; drinking ripples respect facing and running motion uses stride phase.
- New transparent ridge artwork replaces repeated cave-atlas rock piles. Forest-edge ground cover and fallen-branch accents follow tree placement and are cached.
- Follow my citizen restores the account-linked citizen after other selections. Relationship cards show recorded directional trust/familiarity. Life story shows the latest 24 own episodes; browser-local visit bookmarks highlight newer entries. It is not cross-device unread tracking.
- Water crests are batched into six stroke groups rather than two drawing commands per crest.

## Browser experiment
Local WebGL export, in-app Chromium, 1280x720 viewport; synthetic 48x48 world, 32 moving citizens, 16 homes, 240 trees, rain and camera panning. 60 warmup frames then 300 samples. No saved world or backend mutation.

| Mode | Mean FPS | Median ms | P95 ms | Worst ms | Draw calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Balanced before water batching | 12.03 | 76.5 | 122.9 | 174.4 | 268 |
| Performance | 27.54 | 33.7 | 49.8 | 66.8 | 69 |
| Balanced with water batching | 21.88 | 45.0 | 56.8 | 137.2 | 71 |

This is a short rendering experiment, not a promise of 30/60 FPS. Browser scheduling, hardware and scene visibility affect results. It excludes backend/LLM load, network and long saved-world sessions. The final easing and texture import-size changes followed the timing run. Performance quality remains available for slower devices.

To reproduce on a local served Web export: append `?renderer_benchmark=1&quality=balanced` or `quality=performance`. Read the BROWSER_PERF console result. Close other game tabs between runs.

## Validation
23 focused Python tests passed (account boundaries, life history, wildlife routines); a stale deer-night test now derives nighttime from the configured clock rather than assuming tick 18. Godot scenery regression checks include crowd easing, camera position and occupied-home state. Local dashboard visual check used synthetic data; live authentication and account linking were not re-tested.

## Ridge asset
Built-in image generation; asset: client/assets/world/ridge-v1.png. Godot imports at maximum 512 pixels. Prompt: one connected three-peak isometric pixel-art mountain ridge, detailed grey-brown stone, mossy foothills, restrained high snow, upper-left sunlight, transparent background; no trees, people, buildings, ground slab, sky or text. It is decorative terrain artwork, not changed geology or navigation.
