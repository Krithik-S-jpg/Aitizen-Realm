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
