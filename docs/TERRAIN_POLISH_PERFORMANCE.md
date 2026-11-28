# Terrain polish and performance — 2026-11-28

Local changes:
- Mountains participate in depth ordering with citizens, buildings and terrain edges.
- Visual terrace height reduced from 36 to 24 pixels without changing saved elevation or navigation.
- Removed terrain-kit overlays extending beyond cliff footprints; retained connected rock faces, ramps and waterfall geometry.
- Cliff lips follow biome colours, with cached blended top colours.
- Stationary depth order is cached and merged with moving entities.
- Animated terrain visits a cached subset of eligible tiles.

Validation:
- TestTerrainDepth.gd: passed.
- TestNaturalScenery.gd: passed.
- Web release export: passed; staged locally in backend/web.
- Elevated-world preview inspected before the final cache-only changes.

Measurements on this machine (synthetic fixtures, not hosted gameplay):

| Test | FPS | Median ms | P95 ms |
| --- | ---: | ---: | ---: |
| Desktop baseline, dense 64x64 | 41.6 | 21.18 | 36.28 |
| Desktop initial terrain pass | 49.2 | 18.04 | 31.35 |
| Browser earlier baseline, balanced, 32 citizens / 16 homes / rain / camera pan | 17.99 | 52.1 | 77.3 |
| Browser initial terrain pass | 15.71 | 62.7 | 83.2 |
| Browser final cache pass | 14.72 | 66.1 | 82.6 |

Browser runs were not all taken at the same time; system load may differ. These results do not establish a browser improvement. The desktop pass also missed the 55 FPS threshold. No smooth-frame-rate claim is justified.

## Retained rendering follow-up

Static depth objects now own retained CanvasItems. Citizens repaint independently; scenery effects update at staggered 10 Hz intervals. Terrain/world rebuilds invalidate cached commands, and off-screen objects hide and restore correctly. Helper drawing targets follow the retained CanvasItem. Wave buffers accumulate in reference arrays before packing for drawing; rain no longer repeats the same elevated tile pick twice.

The browser now defaults to Performance effects; the settings selector reflects that default. Balanced and High remain available. Performance reduces decorative scenery, precipitation density and ambient birds; it does not change backend simulation speed.

Same-session comparison (same dense surface fixture):

| Build / quality | FPS | Median ms | P95 ms | Worst ms |
| --- | ---: | ---: | ---: | ---: |
| Previous build / Balanced | 13.98 | 70.9 | 86.3 | 102.6 |
| Retained renderer / Balanced | 18.24 | 50.5 | 73.7 | 86.2 |
| Retained renderer / Performance | 30.00 | 33.3 | 33.7 | 36.0 |
| Final export / Performance (later validation) | 29.82 | 33.3 | 42.5 | 75.4 |

No console errors in browser validation. TestRetainedDepth additionally verifies node reuse, hide/restore and invalidation; TestTerrainDepth and TestNaturalScenery pass. The native dense test remains approximately 49 FPS, below its 55 FPS target.

The lower-effects preset is part of the improvement; do not attribute the entire Balanced-to-Performance gain to caching. This is approximately 30 FPS in the local synthetic test, not a 60 FPS guarantee or a hosted-game measurement. Live backend updates and larger worlds need separate profiling.
