# Adult bases and water polish

`adult-bases-v1.png` is an approval concept, not a production sprite atlas.
The user requested approval of both bases before complete animation production.
Do not replace existing walking sprites with these static figures.

## Image generation

Built-in imagegen, transparent-background requested. Prompt: Exactly two full-body adult villagers, male and female; natural seven-and-a-half-head proportions, no chibi or anime, neutral three-quarter standing pose, slightly elevated isometric view, matching scale and upper-left sunlight. Detailed hand-painted raster art matching timber cottages, cliffs and olive forests. Male: muted teal linen tunic, brown trousers, worn boots, short brown hair. Female: sage linen shirt, brown trousers, boots, tied dark-brown hair. Fully clothed, ordinary faces, visible hands, cloth seams, no weapons, no text or borders. This output is a design reference; game-angle sprite production follows approval.

## Implemented

- Water profiles cache valid downstream directions from `flow_to`; river crests advance downstream, lakes retain wind-driven waves.
- Shore wash uses cached bank edges and existing six batched strokes. Visible-tile culling and low-quality disabling remain active.
- Versioned, validated appearance recipe includes base, skin, face, eyes, hair, hair colour, clothing, clothing colour, footwear and facial hair. It is optional for legacy citizens and included in world/player projections.

## Pending after design approval

- Aligned body, face, hair and clothing layers for each direction and action.
- Live turn/animation preview, creator controls and shared game/dashboard compositor.
- Rock eddies, further foliage motion, and visual/performance validation in the hosted browser.

The recipe is a data foundation; it is not yet exposed as working customization. Existing avatars remain usable. No hosted deployment is included in this pass.
