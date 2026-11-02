# Aster human-style rollout

Installed asset: `client/assets/pixel_art/citizens/scout_human_v2.png`.
Explicit frame manifest: `client/config/citizen_human_actions.json`.

The stable `scout` ID now selects human Aster for portraits and core actions. Saved identity, relationships and memory data are unchanged. Native-action detection also selects the same body for surface swimming, underwater swimming and rescue towing, without affecting unmigrated characters.

Four frames each: idle, movement, sleep, gathering, hammer building, swimming, cooking. Hunting uses only the first two clean spear poses; the other two have overlapping bounding rectangles and are excluded. Carry uses walking; chop/mine still alias hammer building as in the existing human profiles. These are not dedicated axe/pickaxe/carry animations. Underwater phases currently share the swimming cycle.

Generated with built-in image generation, using the first Aster draft as edit target. Final prompt:

> Edit this sprite atlas layout ONLY. Preserve this exact human woman identity, outfit, proportions, pixel art and all 32 poses. Arrange 4 columns x8 rows with large fully TRANSPARENT gutters around EVERY sprite. Make ALL sprites smaller within their cells, max 70 percent cell width and 80 percent cell height, including spears and swimming hands. Equal sized cells, absolutely no crossing cell boundaries. Same order: idle, walk, sleep, gather, hammer, swim, cook, spear. No text no grid no backdrop. Ensure wide poses fit fully with empty space. Actual transparent background.

The output still needs explicit rectangles rather than uniform-grid slicing. A connected-component audit located the poses without modifying source pixels. `TestHumanSprites.gd` checks nonempty bounds, transparent background, common texture selection, world height and portrait identity. Full in-game motion acceptance and conversion of remaining identities/ages remain pending.
