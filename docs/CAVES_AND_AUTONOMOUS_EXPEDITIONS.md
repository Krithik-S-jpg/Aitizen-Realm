# Autonomous expeditions and caves

Manual water commands remain available. Autonomous citizens may explore known
shores once healthy (70+), rested (80+), fed and hydrated (both needs <=30), warm,
and free of immediate threats during daylight. Exploration does not override
active work. After a first dive, citizens can gather real wood/fiber, craft a boat,
launch, board, make a short voyage, dive when fit, store marine finds and return.
Manual boat commands cancel the automatic voyage. Missing resources postpone it.

Caves generate at clear walkable mountain edges, capped at 16. Connected local
passages support short out-and-back visits and persistent discovery memories.
Bats rest during daytime and flee nearby visitors; beetles wander the cave floor.
These are initial cave behaviors, not a full subterranean food-chain simulation.
Cave layouts, inhabitants and in-progress trips serialize with the world save.
Existing saves without cave data initialize caves on restoration.

Surface / Underwater / Caves switches observation only. The Caves button focuses
an available entrance; it does not send citizens there. The citizen inspector also
offers exploration of an adjacent cave. No mountain edges means no generated cave.

## Artwork provenance

`client/assets/pixel_art/aquatic/mountains_caves_v1.png` is a generated transparent
4x4 atlas: four mountains, entrance/rocks/mushrooms/crystals, four bat poses and
four beetle poses. Imagegen was used to replace geometric mountain artwork.

Initial prompt: "Use case: stylized-concept. Production sprite atlas for cozy
isometric pixel-art civilization game. Exactly4 columns by4 rows equal cells on
square genuine transparent alpha canvas. Each object centered inside central75%
of cell, generous transparent gutters, no clipping or overlaps. Rich hand-painted
pixel detail with dark outlines matching forest game sprites. Row1 four different
natural mountain ridge masses: broad layered gray rock massif with moss, rugged
brown stratified crag, snowy tall weathered mountain with irregular shoulders, low
broad rocky foothill. NOT geometric pyramids or spikes. Row2 cell1 mossy cave
entrance dark arch in rocky cliff, cell2 cave stalagmite rock cluster, cell3 faint
glowing blue mushrooms, cell4 purple mineral crystal cluster. Row3 four consecutive
flying poses of same small brown bat, wings extended then bent then down then up.
Row4 four consecutive walking poses of same dark cave beetle, legs moving. No
terrain background, text, grid, shadows outside cells, or painted checkerboard.
Exactly16 fully isolated complete sprites."

Correction prompt: "Correct sprite atlas spacing ONLY. Preserve all16 subjects
and same artwork. Re-layout into mathematically exact 4 columns x4 rows equal
square cells, each sprite fitting ENTIRELY in the central60% of its own cell
with20% transparent margins on every side. Make every sprite smaller. Especially
row3 first bat wings must not cross neighboring cell. All mountain bases must fit
inside row1. No clipping, no overlaps, no grid or text. Preserve actual alpha
transparency and row ordering."

Verification: pytest, TestCaves.gd visual capture, and TestDepthControls.gd.
