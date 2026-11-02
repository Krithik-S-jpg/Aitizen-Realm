# Rowan male counterpart

## Corrected v2 and profile UI

The active sheet is now `client/assets/pixel_art/rowan_actions_v2.png`.
The v1 sheet retained inconsistent long hair in working poses; v2 was regenerated
with the built-in image tool, without the female reference. Old files are retained
but no longer used for Rowan. Stable avatar ID and existing saves remain unchanged.

V2 prompt: Production 2D hand-painted pixel-art sprite atlas; same adult male
medieval villager in every frame, SHORT cropped brown hair, short beard, teal
linen shirt, brown trousers and boots. No long hair, ponytail or braid. Exactly
four columns and eight rows: idle, walking with alternating legs, curled sleeping,
crouched gathering, hammer building, horizontal swimming, stirring cooking,
short-spear hunting. Entire figures and tools inside cells with 15 percent empty
transparent margins. Same face, proportions and scale, isometric three-quarter
right-facing. No text, grid or scenery; transparent alpha.

Citizen selection now opens a full profile with portrait, live needs bars and
separate life/decision and action/communication tabs. Hunger/thirst bars show
need pressure (higher is worse); health/energy show condition (higher is better).

Generated using the built-in image-generation tool with Juniper as a style/layout
reference. Saved to `client/assets/pixel_art/rowan_actions_v1.png`.
Selectable as **Rowan (new)** in Citizens and new-world settings. This avoids
confusion with the older appearance named Rowan (legacy ID `cook`). Stable new ID:
`rowan`. Gender remains independently selectable.

Eight four-frame rows: idle, walking, sleeping, gathering, building, swimming,
cooking, hunting. Surface and underwater rendering use the same identity.
Existing characters and saves are unchanged. The atlas is generated art; frame
availability tests do not guarantee perfectly smooth motion or anatomical consistency.

## Generation prompt

Use case: stylized-concept. Image 1 is a style and animation-layout reference.
Create a matching adult MALE counterpart called Rowan: short chestnut hair,
subtle stubble, masculine adult face and build, teal linen tunic, brown trousers
and boots, belt pouch. Same hand-painted pixel-game style and 3/4 right facing
angle as reference. Production sprite atlas EXACTLY 4 columns x 8 rows of equal
rectangular cells, transparent alpha background. 32 full-body sprites, FOUR
distinct sequential frames per row. Rows: 1 idle breathing, 2 walking cycle,
3 curled sleeping, 4 gathering reaching, 5 building hammer swing, 6 horizontal
swimming strokes, 7 cooking stirring pan, 8 wooden spear hunting thrust. Keep
identical male identity and clothing across every frame. Critical: all limbs and
tools entirely within their own cell with generous transparent padding on all
four sides, no neighboring overlap, no cropping. Scale character smaller to
ensure spear fits. Consistent scale and baseline within each row. No text,
labels, grid lines, scenery or other characters. This is a new male atlas,
do not reproduce the female reference.
