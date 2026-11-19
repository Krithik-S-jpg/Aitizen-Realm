# Natural world rendering pass — 2026-11-19

Visual changes use the existing isometric artwork. Simulation terrain, navigation,
resource quantities and collision rules are unchanged.

- Ground mesh vertices share neighbouring terrain colours; world-space variation
  reduces uniform ground without another texture sample.
- Broad shore shallows and darker open water replace bright tile-edge strokes.
- Ground litter and stationary resource shadows are combined in one scenery mesh.
- Trees vary deterministically in height; small plants and animals use smaller,
  more believable proportions. Mountain artwork is less oversized.
- Finished buildings receive foundations and a worn doorstep. No decorative
  stockpiles are represented as real supplies.
- Day-phase tint changes fade; fuelled fires receive a restrained night glow.
- Tree sway is gentler. Existing distance-driven citizen walking is preserved.

## Performance evidence

Godot 4.7, Compatibility renderer, Intel UHD Graphics, 1152×648, vsync disabled,
uncapped desktop benchmark. Existing `BenchmarkWorldRenderer.gd`: dense 64×64
fixture, 520 resources, 48 entities, rain/wind, 60 warmup + 300 measured frames.

| Measurement | Before | Final |
|---|---:|---:|
| Average FPS | 39.0 | 56.8 |
| Median frame, ms | 21.93 | 16.27 |
| p95 frame, ms | 44.43 | 30.86 |
| Worst sampled frame, ms | 112.68 | 55.33 |
| Last-frame draw calls | 673 | 280 |

An intermediate unbatched implementation regressed to 29.3 FPS / 2111 draw calls
and was replaced. These are single local runs, not a guarantee across devices.
The fixture does not measure full-game networking, browser overhead, initial mesh
construction, or a large settlement. Browser/mobile acceptance remains required.

Performance quality disables the added scenery mesh and ambient water strokes;
balanced/high use the batch. Surface details hide in cave/underwater views.
Entity snapshots do not rebuild scenery; resource placement and quality changes do.

## Validation

`TestNaturalScenery.gd` checks shared-edge colours, caching across citizen updates,
resource invalidation, quality changes and observation-layer isolation.
`PreviewNaturalWorld.gd` renders a repeatable river/forest/village composition.
The Web export was rebuilt using the existing Web preset.

## Remaining art work

This is a rendering pass, not a replacement asset collection. Dedicated continuous
ridge artwork, rounded shoreline geometry, richer home props and species-specific
animation refinements remain future work. Full-game browser FPS is not yet measured.
