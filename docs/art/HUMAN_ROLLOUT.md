# Human character rollout

Generated using the built-in image-generation skill. Stable saved avatar IDs are unchanged.

## Installed

Seven replacement adult sheets (builder, herbalist, scholar, cook, miner, fisher, artisan), nine basic age profiles (infant; male/female toddler, child, teen, elder), explicit Juniper/Rowan frame corrections and separate hunting textures. All sheets live in `client/assets/pixel_art/citizens/`; the explicit manifest is `client/config/citizen_human_actions.json`.

Profiles now use the same age-specific appearance as the world. Carried children retain child art. Adult scale is 48 world pixels; stages use 18/25/34/43/44 pixels for infant/toddler/child/teen/elder.

## Limits

Age sheets cover idle, two movement poses and sleep only. Elders' work and aquatic actions currently fall back to their idle pose; dedicated play, teaching, caregiving, carrying, diving and age-specific work cycles remain unfinished. Adult chop/mine still alias hammer and carry aliases walking. Gender does not automatically replace a chosen adult appearance. Age profiles are shared presets, not unique aging versions of every identity. Some separate hunting rows have tiny adjacent-row edge pixels (7-28 source pixels); rendered preview is checked at world scale, but these still need source-art cleanup before claiming pixel-perfect assets.

The test scene renders four animation phases through WorldRenderer without touching a saved world. This is not a long-running saved-world acceptance test.

## Prompts and asset paths

### builder_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Ember, adult woman with deep brown skin, short black curls, rust-red tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### herbalist_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Fern, adult woman with light freckled skin, long red braid, olive green tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### scholar_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Lumen, adult man with light skin, straight black hair, clean shaven, indigo tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### cook_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Rowan classic, adult woman with medium brown skin, dark tied-back hair, burgundy tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### miner_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Saffron, adult man with tan skin, blond short hair and beard, ochre tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### fisher_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Tide, adult man with dark skin, short dark hair, blue tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### artisan_human_v2.png

Generate a transparent game sprite atlas matching the input human-proportioned pixel-art style. NEW identity: Violet, adult woman with light olive skin, short wavy dark hair, plum tunic, brown trousers and boots. Same identity and proportions in EVERY frame. Exactly FOUR columns EIGHT rows. Rows in order: idle breathing, walking, curled sleeping, crouched gathering, hammer building, horizontal swimming, cooking stirring pot, spear hunting. Four sequential poses per row. Large TRANSPARENT gutters, each entire pose INCLUDING tools inside its own cell. Same physical body scale throughout, not chibi. Same right-facing three-quarter camera and upper-left lighting. No labels, background, grid or floor shadows. Use only 65% cell width, 75% height; no touching neighbors.

### family_human_v2.png

Create ONE transparent age-stage sprite atlas in the same natural human-proportioned pixel art style as reference (NOT chibi, not oversized cartoon heads). EXACTLY 4 columns and 9 rows, 36 isolated full-body figures. Large transparent padding between cells, no background text or labels. Each row is a DIFFERENT age identity; each has 4 poses left to right: idle, movement stride A, movement stride B, curled sleeping. Row1 infant in cream romper: sitting, crawling A, crawling B, sleeping. Row2 toddler boy age2 ochre tunic; Row3 toddler girl age2 green tunic; Row4 child boy age8 brown skin curly hair blue tunic; Row5 child girl age8 auburn braid green tunic; Row6 teen boy age15 dark hair blue tunic, adolescent anatomy; Row7 teen girl age15 dark braid plum tunic, adolescent anatomy; Row8 elderly man grey beard ochre tunic, slight stoop; Row9 elderly woman grey bun plum tunic slight stoop. Modest fully clothed all ages brown trousers boots except infant. Consistent face/clothes within each row, correct human age anatomy (NOT just scaled adults). Same 3/4 right view, same upper-left light. All poses fully within cells; wide gutters. Transparent background.

### hunting_human_v2.png

Transparent pixel art hunting animation atlas, human-proportioned style matching references. EXACT TWO columns SEVEN rows, 14 figures total. Each row a distinct adult: row1 Ember dark-skinned woman black curls rust tunic; row2 Fern light freckled woman red braid olive tunic; row3 Lumen light skinned clean-shaven man black hair indigo tunic; row4 Rowan woman medium brown skin dark tied hair burgundy tunic; row5 Saffron tan man blond beard ochre tunic; row6 Tide dark-skinned man short hair blue tunic; row7 Violet light olive woman wavy dark hair plum tunic. Brown trousers boots all. Two right-facing spear hunting poses each: ready with spear held near body and forward short thrust. Short spear, tip fully within each cell. Extremely wide transparent gutters. Full body natural anatomy consistent identity between frames. Each sprite with weapon fits central 65 percent of cell. No text no background. Same slightly overhead three-quarter view and pixel shading as reference. Fourteen isolated poses, no overlaps.

### juniper_rowan_hunt_v2.png

Transparent sprite atlas exactly TWO columns TWO rows. Four full-body human pixel-art sprites matching reference style, no chibi. Row1 Juniper adult woman auburn long braid teal tunic brown trousers boots. Row2 Rowan adult man short brown hair full brown beard teal workshirt brown trousers boots. Each row two hunting animation poses facing three-quarter right: ready holding short spear then controlled forward thrust. Preserve same person's face hair outfit body scale in both poses. VERY LARGE transparent gutters at least 15% between all figures and rows, spear tips wholly inside each cell. All figures same physical size, full boots visible. No scenery no floor no text. Human anatomy consistent with reference.

