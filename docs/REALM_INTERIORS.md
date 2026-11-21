# Cave and underwater visual update

The renderer now uses continuous, repeating floor materials with linear filtering. Cave limestone and underwater sand replace individual paving-like tiles. Shared corner depth colours soften transitions between shallow and deeper seabed. Textures are loaded once and reused; off-screen props are culled.

The interior prop atlas supplies rock walls, mineral veins, crystals, pools, inscriptions, coral, kelp, seagrass, wrecks, ruins and cave entrances. A separate four-frame wildlife atlas provides fish, crabs, jellyfish, sharks, bats and cave beetles. Surveyed cave floors respect exploration records. Prepared cave explorers receive the lamp glow.

## Related simulation work

- New version-2 building foundations reserve their footprint and doorway. Placement and path planning agree on blocked ground. Existing version-1 buildings retain their original footprint for save compatibility.
- Worn entrance paths search around solid obstacles; these are visual paths, not free constructed roads.
- Cave surveys persist, mineral deposits are finite, and reported routes preserve the source citizen separately from personal exploration. Unstable passages warn explorers to turn back.
- Dive access and oxygen costs account for depth, current, visibility, temperature and equipment. Existing party rescue remains in use.

These changes do not add cave collapse physics or physical underwater current displacement.

## Generated artwork

Built-in ImageGen was used, with transparent generation for prop/wildlife atlases, a background-removal edit for wildlife, and opaque generation for ground materials. Runtime files are in `client/assets/world/cohesive/`:

| File | Prompt direction |
| --- | --- |
| `interiors.png` | Naturalistic muted pixel-art isometric RPG props, upper-left lighting, transparent 4-by-4 atlas. Rock walls, stalagmites, ore, crystals, pool, ruins, inscription, supplies, coral, kelp, shellfish, columns, wreck, sea arch, seagrass and entrance. Isolated objects, no labels or grid. |
| `interior-wildlife.png` | Consistent realistic anatomy, four animation frames per species, six rows: fish, crab, jellyfish, shark, bat and cave beetle. Tail, leg and wing phases; centered consistent proportions; transparent background. |
| `cave-floor.png` | Seamless overhead grey-brown limestone sediment, fine grains and shallow cracks; diffuse neutral lighting; no paving, grid, props or perspective. |
| `seabed-floor.png` | Seamless overhead pale beige sand with gentle ripple ridges, tiny pebbles and shell fragments; no blue filter or large objects. |

## Verification

- 24 targeted backend checks passed for realm interiors, diving, expedition parties and memory communication (API startup tests excluded).
- Earlier related settlement/storage/expedition regression run: 33 passed, including the long village survival scenario.
- Godot `TestNaturalScenery.gd` passed: cached scenery, layer isolation, quality controls and resource invalidation.
- Godot Web release export succeeded and was staged into `backend/web`.
- Rendered previews: `client/.agent-qa/cave-cohesive-preview.png` and `client/.agent-qa/underwater-cohesive-preview.png`.
- Live browser automation timed out. Browser FPS and hosted saved-world acceptance remain unverified. Synthetic benchmark supports `?renderer_benchmark=1&quality=balanced&environment=surface` (or `cave`, `underwater`); it does not mutate a backend world.

No zero-frame-drop guarantee is implied by the export or headless tests.
