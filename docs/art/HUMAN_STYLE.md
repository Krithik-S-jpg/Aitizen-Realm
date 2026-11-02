# Human character style reference

Status: visual proposal, not a runtime sprite atlas. Existing game assets are unchanged.

Reference: `human-style-lineup-v1.png`, generated with the built-in image-generation tool using Juniper v1 and Rowan v2 action atlases as visual references.

Review: the four figures share clothing treatment, lighting, viewing angle and rendering style. The child has different proportions and the elder has an aged silhouette. The result remains stylized; review the head sizes before committing to full animation production.

Next gate: approve this visual direction before generating identity-specific animation sheets. Keep saved avatar IDs stable. Each replacement needs complete action coverage, consistent foot anchors, verified transparent cell bounds and in-game scale checks. Do not use this static lineup as a replacement for working animations.

## Generation prompt

Use case: stylized-concept. Asset type: Aitizen Realm character art direction reference lineup, NOT an animation atlas. Input images: Juniper and Rowan action sheets are style references for clothing, pixel detailing and isometric viewpoint. Generate ONE transparent reference lineup with exactly four distinct full-body humans: adult woman with auburn braid and teal work tunic, adult man with dark hair and short beard and ochre work shirt, a school-age child with dark skin and curly hair wearing a modest green tunic, and an elderly woman with gray tied hair and plum clothing. All four belong to precisely the same natural-proportioned pixel-art game world, same pixel density, shading and three-quarter slightly overhead camera facing right. Adults about 6.5 heads tall, child anatomically age appropriate about 5 heads tall and 65 percent adult height, elder naturally aged with slight stoop. All feet on same baseline, ample separation, no overlap. Rich restrained earthy palette, readable crisp pixel clusters, consistent upper-left illumination, realistic small eyes and hands, believable human limbs, no enormous heads, no chibi, no anime doll faces, no photorealism, no different art styles. Full figures including feet entirely visible, neutral idle poses. Truly transparent background, no scenery, no captions, no text, no grid. This is a coherent art direction proof for replacing mixed cartoon and human characters.
