# Raised terrain

New generated terrain uses saved terrace levels (0â€“4), connected stair edges and downstream river levels. Legacy flat checkpoints are upgraded on restore in the loaded copy. Stored checkpoints are not overwritten. Existing structures and their immediate surroundings are kept level; original walkable land edges receive ramps where needed. Resources and citizens are preserved. Save the upgraded world as a new checkpoint to retain the old backup. Already elevated saves retain their terrain layout.

Navigation and animal movement reject unmarked cliff crossings. Harvesting checks the actor terrace. Foundations and entrances must share a level and cannot occupy stairs. Completed bridges use the height of matching opposite banks while the water remains below the deck.

The renderer offsets terrain and objects, depth-sorts raised caps with citizens and scenery, draws textured cliff faces and waterfall streaks, and interpolates movement heights. Decorative ground meshes are cached per raised tile. This is discrete 2.5D elevation, not a 3D physics engine.

Validation: 14 focused Python tests passed (elevation, interiors and water travel), Godot cached-scenery regression passed, elevated-world preview rendered with coordinate-picking assertions, Web release export completed. Hosted browser FPS and a long-running populated elevated settlement have not yet been measured. Existing terrain artwork and mountain anchors are retained; exact reference-image appearance is not guaranteed.

## Cliff texture provenance
Generated with the built-in image generation tool, opaque new texture, at client/assets/world/cohesive/cliff-face.png. Prompt: seamless tileable vertical natural cliff rock face, straight-on orthographic; detailed naturalistic pixel art; muted warm gray and taupe limestone, irregular angular slabs and fractured columns, subtle strata, medium-scale cracks and small ledges, restrained moss, diffuse upper-left light; no grass top, sky, objects, text, border or perspective. Texture is mapped onto cliff sides.

## Natural detail pass
Neighbor-weighted elevation reduces isolated pillars in newly generated terrain. Cliff rims include broken sod, moss, shaded facets and toe rubble. Shoreline reeds use the cached scenery mesh; waterfall foam animates only on visible faces. Six elevation regressions and the Godot scenery check passed after this pass; browser export rebuilt. Hosted FPS remains unmeasured.

## Legacy upgrade and broader landforms
Elevation is smoothed over a weighted seven-by-seven neighborhood for new terrain. Visual terrace steps are 36 pixels (previously 24). Fifteen focused tests pass, including legacy content preservation, level foundations, traversable land edges and idempotent migration. Live hosted-save verification and FPS measurements remain pending.

## Landscape and crossing pass
River routing uses a bounded low-frequency bend preference while retaining uphill penalties and a connected drainage route. Occasional shallow pockets vary channel width and resources are cleared from carved water. Forest resource placement uses coherent density patches to form groves and clearings.

Construction preferences cluster homes near communal anchors and farms near homes within the same nearby search radius; they do not relocate existing buildings or create a fixed town plan. Existing doorway paths and stockpile decoration remain. This is not a complete settlement planner.

Cliffs have shaded recesses; stairs extend along a slope with visible treads; procedural bridge planks and rails orient to opposite banks at deck height. High terraces receive a restrained aerial tint and shoreline reeds are less repetitive. No new mountain artwork or full distance-fog system was added in this pass.

Validation: 18 tests passed including the settlement-life simulation; Godot cached-scenery regression and elevated preview passed. Hosted browser frame-time testing remains pending.

## Renderer optimization
Cache terrain positions and static depth records; cull before adding static records to the per-frame sort. Plateau interiors use the static terrain/scenery meshes; only exposed terrace edges are redrawn in the occlusion queue. Regression check passed.

Desktop GL Compatibility benchmark: elevated 64x64 fixture, 520 resources, 48 entities, 1152x648 on Intel UHD. Final run 50.8 FPS, median 17.31 ms, p95 31.38 ms, worst 38.70 ms, 186 draw calls. The benchmark exited 1 because its performance target was not met. Earlier intermediate run: 27.2 FPS and 723 calls, but preview activity overlapped that run, so this is not a controlled speedup measurement. Not a hosted-browser result.

## Shared courts and style
Completed wells/campfires anchor derived courts on clear level ground. Bounded pathfinding connects nearby completed home/workshop/storage/farm entrances via actual walkable cells, ramps and completed bridges. New solid construction cannot occupy designated court cells. Existing buildings/resources are never moved. Layout refreshes on structure changes or every 120 ticks; terrain metadata may require a world refresh in clients. This does not automatically construct new bridges or manufacture materials.

Cached court/path artwork, beveled exposed cliff corners and RealmStyle's shared building proportions, rock lighting and shadow palette integrate with existing slope/waterfall geometry. These are procedural textured pieces, not a newly illustrated sprite atlas. Existing animal/character art is retained.

Validation: 10 elevation/settlement-life tests plus one court/path preservation test passed; Godot scenery regression and preview passed. Hosted FPS is not remeasured for this pass.
