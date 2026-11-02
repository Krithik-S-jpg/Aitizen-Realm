# Aquatic assets and validation

Generated with the built-in image-generation tool. Original alpha preserved; no programmatic image editing. Files: swimming_atlas.png (six poses x eight appearance rows), marine_atlas.png (four boat frames, four kelp frames, four seabed objects, four fish frames). Runtime plays source poses; these are not 24 unique frames.

The underwater layer uses existing water coordinates. Citizens request short dives from shore or an anchored expedition boat. Backend-owned marine animals now replace ambient fish. Habitats, finite harvests, discoveries, boat occupancy and cargo persist in world checkpoints. See `docs/UNDERWATER_EXPEDITIONS.md` for controls, safety limits and verification. Eight aquatic color variants map to existing appearance IDs; they are not exact replicas of every original costume.

Additional generated assets: `marine_life_v1.png` (4x4 atlas: fish, crab and jellyfish four poses each; shark, wreck, cave and oyster) and `diving_actions_v1.png` (6x8 atlas: two descent, two gathering and two surfacing poses per appearance). Original alpha preserved. No claim of 24 unique frames; rendering interpolation and source-frame animation are separate. Graphical preview captures are in client/.agent-qa.

## October expedition asset prompts

Both assets used the built-in image-generation tool, not the API/CLI fallback.

### marine_life_v1

Use case: stylized-concept. Asset type: production sprite atlas for isometric pixel-art settlement game. Create a precisely aligned 4 columns by 4 rows sprite sheet on genuine transparent alpha background, square canvas. Each cell equal size, centered object within cell, generous 20% transparent gutters, absolutely no objects crossing cell edges. No text, no grid lines, no background. Detailed hand-painted pixel art, teal blue marine palette, consistent isometric three-quarter view. Row 1: four consecutive animation poses of SAME small silver-blue reef fish swimming facing right, tail moving. Row 2: four consecutive walking poses of SAME red-orange crab facing right, legs moving. Row 3: four consecutive pulse poses of SAME translucent blue jellyfish, tentacles curled differently. Row 4: cell1 a gray reef shark facing right, cell2 small broken wooden sunken boat wreck with seaweed, cell3 submerged rocky cave entrance, cell4 open oyster with one pearl. Exactly 16 isolated sprites, clean alpha silhouettes, no shadows outside cells.

### diving_actions_v1

Reference/edit target: swimming_atlas.png. Use case: identity-preserve. Edit this sprite sheet into a companion underwater action atlas. Keep EXACTLY 8 rows and 6 columns equal cells, same eight character identities in same row order, hood colors, faces, pixel art style, transparent alpha. Change poses only. Columns1 and2: two different consecutive diving DOWN poses angled head-first lower right arms forward legs kicking. Columns3 and4: two different consecutive underwater gathering poses crouched reaching down to pick up a small shell then pulling shell toward chest. Columns5 and6: two different consecutive surfacing poses swimming UP diagonally upper right head raised arms upward legs kicking. Entire body must fit within each cell with generous transparent gutters; centered same scale in every cell. Exactly48sprites, no additional objects outside hands, no borders no words no checkerboard no scene background. Preserve real transparency. Do not duplicate original horizontal swim poses.

## Prompts

### water_prompt

Use case: stylized-concept. Asset type: production transparent sprite atlas for cozy isometric pixel-art civilization game. Make a perfectly regular 6 columns by 8 rows sprite sheet, 1536x2048 pixels. Each cell 256x256 with generous transparent margins and one full-body chibi citizen swimming horizontally toward the right, viewed three-quarter from above. Six sequential crawl/breaststroke swim poses per row with changing arm reach and leg kick, consistent head placement and scale. All bodies fully visible (for underwater), no water or scenery. Row1 teal hood ivory trim brown hair; row2 blue hood dark hair; row3 green hood auburn hair; row4 purple hood dark hair; row5 orange hood brown hair; row6 ochre hood blond hair; row7 navy hood dark skin; row8 burgundy hood brown hair. Charming hand-painted pixel texture, crisp outline, warm face, same proportions every frame. No text, no labels, no grids, no shadows or checkerboard. True transparent background. Exactly48 complete separated poses. Each pose fits centrally inside its cell, no touching neighboring cells.

### swim_edit_prompt

Edit this sprite atlas only to correct framing. Keep exactly the SAME 8 citizen identities and six different swimming poses per row, same artwork style. Re-layout every sprite much SMALLER inside an exact regular 6-column by8-row grid. Each sprite must fit wholly within the central60% of its own cell. Minimum20% clear transparent padding on ALL FOUR sides of EVERYcell. Outer canvas margin too. No limbs crossing cell boundaries, no clipped feet at edges. Full bodies swimming right, clean true alpha. No labels or drawn grid. Preserve eightrows and sixcolumns.

### marine_prompt

Use case: stylized-concept. Generate a transparent game animation atlas, exactly 4 columns and 4 rows of evenly spaced cells. Cozy hand-painted pixel-art isometric assets, crisp dark outlines and richly shaded surfaces. One asset per cell, SMALL and centered within the middle 60% of cell with generous empty margins; never touch cell edges. Row1: four consecutive frames of an EMPTY wooden rowboat facing right with two oars in different rowing positions, no passenger, identical hull, 3/4 top down view. Row2: four consecutive swaying poses of tall turquoise kelp. Row3: pink coral, blue seabed rock, golden shell cluster, sea grass. Row4: four successive frames of a small silver fish swimming right with tail movement. No ground tile, water background, text, labels, grids or shadows. Genuine transparent background. Assets for a civilization game's underwater layer.

### marine_edit_prompt

Use case: background-extraction. Remove ALL colored hazy background from this atlas, preserve only the sixteen boat, kelp, coral, rock, shells, grass and fish sprite silhouettes. GENUINE alpha transparency everywhere else, including between oars and hull. Do not paint a replacement backdrop. Keep exact canvas size, grid locations, cell ordering, sprite outlines and colors. No glow, no shadows. Clean transparent game sprite sheet.

