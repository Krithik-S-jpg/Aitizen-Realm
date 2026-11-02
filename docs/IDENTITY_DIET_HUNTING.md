# Identity, diet and hunting

Citizen creation now offers gender (unspecified, female, male, nonbinary) and diet
(omnivore or vegetarian). Neither assigns a profession or skill. These fields
persist in world saves; older saves default to unspecified/omnivore. Both utility
decisions and local-model observations use diet. Citizens do not randomly change
the user's dietary choice.

Hungry, healthy omnivores with a crafted hunting spear may pursue known nearby
rabbits or deer. Pursuits are bounded; deer can injure hunters. A successful hunt
leaves an actual carcass, not free inventory. Citizens gather meat, cook it at a
fueled campfire, and eat. Vegetarian eating and resource gifts reject animal food.
Existing legacy meat remains edible for compatibility; cooking provides better
nutrition. This is a first hunting implementation, not a complete wildlife balance
or a new generations system.

## Juniper asset

Generated with the built-in image-generation tool, saved at
`client/assets/pixel_art/juniper_actions_v1.png`. Four poses per row: idle, walking,
sleeping, gathering, building, swimming, cooking, hunting. Existing appearances
are retained; gender is independent of appearance. Old appearances use a procedural
spear cue. Additional age-specific art and families remain future work.

Generation prompt: One consistent adult female village citizen called Juniper,
chestnut braid, teal linen tunic, brown trousers and boots, small belt pouch.
Detailed hand-painted pixel-art aesthetic for an isometric medieval village game,
full body three-quarter facing right. Exactly four columns and eight rows on a
transparent background, no text or grid lines. Equal cells, generous margins,
same scale and foot baseline. Four sequential frames per row: idle breathing,
walking, curled sleeping, gathering, hammer building, horizontal swimming,
stirring cooking, wooden spear hunting. Consistent face, hair, outfit and adult
proportions; no gore, scenery or extra characters.

Tests cover physical hunt/harvest/cook/eat, dietary rejection, legacy identity
defaults, identity serialization, and atlas frame availability. These are not a
claim of measured rendering FPS or complete visual acceptance testing.
