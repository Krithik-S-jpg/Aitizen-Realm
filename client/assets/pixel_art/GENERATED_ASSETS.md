# Generated animation assets

Generation mode: built-in `imagegen`.

## Aitizen 24-frame action atlas

Final asset: `aitizen_character_actions_v3_24f_clean.png`

Final prompt:

> Use case: stylized-concept. Asset type: production isometric game character animation sprite atlas for Aitizen Realm. Input images: Image 1 is the identity and art-style reference for the teal-hooded Aitizen character. Primary request: create exactly 24 isolated full-body animation frames in a strict 6 columns by 4 rows grid. Row 1: six-frame seamless walk/run cycle. Row 2: six-frame axe chopping cycle from wind-up through impact and recovery. Row 3: six-frame pickaxe mining cycle from wind-up through impact and recovery. Row 4: first three frames gathering/picking up resources, last three frames carrying wood and building with a hammer. Style/medium: polished cozy fantasy isometric pixel-art-like game sprite matching the reference character exactly; crisp readable silhouette at small scale. Composition/framing: character scale, ground contact, facing direction, camera angle, and cell alignment identical in every frame; generous transparent padding; one character per cell. Lighting/mood: consistent soft upper-left daylight. Constraints: true transparent PNG alpha; exact 6 by 4 uniform grid; preserve teal hood, cream trim, brown backpack, proportions, face, and palette; tools only in relevant rows; no labels, text, borders, grid lines, glow, background, or shadows extending between cells. Avoid: duplicated poses, cropped limbs or tools, inconsistent identity, changing clothes, merged frames, colored fringe pixels, checkerboard background.

## Deer, rabbit, boar, and wolf 48-frame atlas

Final asset: `wildlife_actions_v2_48f_clean.png`

Final prompt:

> Use case: stylized-concept. Asset type: production isometric wildlife animation sprite atlas for Aitizen Realm. Input images: Image 1 is the exact species identity and cozy fantasy art-style reference. Primary request: create exactly 48 isolated animal frames in a strict 6 columns by 8 rows grid. Rows 1-2 are deer: row 1 six-frame walk/run cycle, row 2 six behavior poses progressing through grazing, drinking, alert, lying down, sleeping, rising. Rows 3-4 are rabbit with the same locomotion row then forage/drink/alert/sleep behavior row. Rows 5-6 are wild boar with a walk/run row then rooting/eating/drinking/alert/sleep behavior row. Rows 7-8 are grey wolf with a run/hunt row then stalk/pounce/feed/drink/howl/sleep behavior row. Style/medium: polished cozy fantasy isometric pixel-art-like game sprites matching the reference species; crisp readable silhouettes at small scale. Composition/framing: strict uniform cells; one complete animal per cell; consistent species scale, ground contact, camera angle and facing direction; generous transparent padding. Lighting/mood: consistent soft upper-left daylight. Constraints: true transparent PNG alpha; exact 6 by 8 grid; preserve animal anatomy and colors across every frame; no scenery, grass, prey, blood, text, labels, borders, grid lines, glow, cast shadows, or overlap between cells. Avoid: duplicated poses, cropped animals, anatomy mutations, merged frames, inconsistent size or identity, checkerboard background, colored fringe pixels.

## Fox, bear, goat, and duck 48-frame atlas

Final asset: `wildlife_actions_v3_48f_clean.png`

Final prompt:

> Use case: stylized-concept. Asset type: second production isometric wildlife animation sprite atlas for Aitizen Realm. Input images: Image 1 is the exact cozy fantasy wildlife art style, scale, lighting and grid reference. Primary request: create exactly 48 isolated animal frames in a strict 6 columns by 8 rows grid. Rows 1-2 are red fox: six-frame run/stalk cycle, then six poses for pounce, catch food, eat, drink, curl up, sleep. Rows 3-4 are brown bear: six-frame walk cycle, then six poses for berry foraging, eating, drinking, standing alert, lying down, sleeping. Rows 5-6 are mountain goat: six-frame sure-footed walk/climb cycle, then six poses for grazing, eating, drinking, alert, lying down, sleeping. Rows 7-8 are mallard duck: six-frame waddling/swimming cycle, then six poses for pecking, dabbling, drinking, alert, resting, sleeping. Style/medium: polished cozy fantasy isometric pixel-art-like game sprites matching the reference; crisp readable silhouettes at small scale. Composition/framing: exact uniform cells; one complete animal per cell; consistent scale, ground contact, camera angle and facing; generous transparent padding. Lighting/mood: consistent soft upper-left daylight. Constraints: true transparent PNG alpha; exact 6 by 8 layout; preserve anatomy, species identity and colors; no scenery, prey, blood, labels, text, borders, grid lines, glow, cast shadows, or overlapping cells. Avoid: duplicated poses, cropped animals, anatomy mutations, checkerboard background, white matte, colored fringes, merged frames.

The generated images used a baked checkerboard despite the alpha request. `client/tools/ExtractSpriteAlpha.gd` performs the deterministic cleanup that produced the final `*_clean.png` files used by the game.
