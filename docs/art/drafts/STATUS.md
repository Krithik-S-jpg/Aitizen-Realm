# Human animation production: first batch

The user approved the human-style lineup. Generated with the built-in image-generation tool, using `../human-style-lineup-v1.png` as the visual reference.

These are draft sources, NOT runtime replacements. Citizen IDs, saved worlds, and existing animation mappings have not been changed.

## Assets and review

- `aster-actions-human-v1.png`: 32 poses, eight actions. Transparent corner verified. Uneven row spacing and crowded poses make automatic 4x8 grid extraction unsafe. Needs corrected layout or individually verified frame rectangles before integration.
- `aster-walk-human-v1.png`: eight walking poses in a 4x2 layout. Separate experimental walk cycle, not a complete identity replacement. Requires alpha and in-game motion review.

Do not replace only the walk cycle while leaving chibi work/swimming frames active: that would make the same citizen change body style between actions. Promote a complete, verified identity together.

## Prompts

Actions: Create a production transparent sprite animation atlas for Aitizen Realm. Reference image is APPROVED human style, match its natural human proportions and pixel shading, NOT chibi. ONE consistent adult woman Aster: ash-brown short hair, teal hood worn down, teal tunic, brown trousers and boots, small realistic eyes. Exactly 4 columns and 8 equal-height rows, 32 separate full-body sprites, each wholly inside its cell with generous transparent padding. Same character face, outfit, size and three-quarter right facing camera throughout. Row1 four idle breathing frames; row2 four walking cycle frames; row3 four curled sleeping frames; row4 four crouching gathering frames; row5 four hammer building frames; row6 four horizontal swimming strokes; row7 four stirring cooking pot frames; row8 four spear hunting thrust frames. No letters, no labels, no gridlines, no scenery, no shadows outside cells. Transparent background. Strong readable silhouettes matching reference woman anatomy; no cartoon oversized head. Atlas aspect 1:2, regular exact 4 by 8 grid.

Walk: Create ONE production sprite sheet: Aster adult human woman, short brown hair teal tunic brown trousers boots matching approved reference natural proportions. EXACT 4 columns by 2 rows EQUAL cells. ONLY eight WALK CYCLE frames in order, all standing same height, baseline identical within each cell, facing three-quarter right. Each figure uses only central 60 percent of its cell width and 75 percent height. Wide transparent gutters. No props or text. Crisp pixel art, small human eyes not chibi. All frames same identity and clothes. Row1 walk frames 1-4, row2 walk frames5-8. Actual transparent background.

## Remaining

Correct and verify the first action atlas; implement stable explicit frame manifests and motion/foot-anchor tests; generate remaining adult identities and all age stages; update portraits and special action render paths; perform in-game visual acceptance. No full rollout is claimed by this batch.
