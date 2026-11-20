# Cohesive world artwork — 20 November 2026

## Assets and integration
Built-in image generation produced these transparent atlas files under `client/assets/world/cohesive/`:
- resources.png: 16 sprites covering young/mature trees, conifers, fruit tree, shrubs, flowering plant, mushrooms, rocks, ore, clay, log and stump.
- structures.png: 12 sprites covering house, tent, storage, cooking fire, workbench, well, garden, fence, furnace, bridge, boat and fishing rack.
- items.png: 16 sprites covering materials, food and tools. Crafting cards and carried stone/fruit use the shared atlas where keys match.
- wildlife-primary.png and wildlife-secondary.png: eight species retaining six-column/eight-row action layouts.

All use muted natural colours, detailed pixel clusters and upper-left lighting. Atlas regions are measured from source alpha, not guessed equal-cell crops. `CohesiveArt.gd` caches textures and UI icons. Original terrain artwork is retained. Source atlases are preserved for rollback; the three superseded runtime atlases are excluded from Web exports.

House height is 140 world pixels (formerly 104); mature tree heights follow growth with a higher canopy. Larger artwork does not change collision footprints. Existing animation and simulation behavior is retained: work/construction overlays, fuel-aware fires, crop motion, boat motion and species actions. New furnace/fishing-rack art does not add backend blueprints or new gameplay systems. This pass does not replace every aquatic/biome-specific asset or create additional animal sprint frames.

## Prompt set
1. Resources: exact 4x4 grid, realistic isometric pixel-art vegetation and materials, natural branching, muted olive foliage/brown bark, upper-left light, transparent padding; young deciduous, medium deciduous, mature oak, young/mature conifer, apple tree, two rocks, herb, shrub, berry bush, mushrooms, log, stump, ore, clay.
2. Structures: exact 4x3 grid of timber cottage, tent, shed, cooking fire, workbench, well, garden, fence, furnace, bridge, boat and fishing rack; slate roofs, stone foundations, realistic doors and tools; no people, text or scenery.
3. Wildlife primary: restyle the existing six-column eight-row deer/rabbit/boar/wolf atlas while preserving species, pose, limb positions, orientation and cell placement; natural eyes/fur and genuine transparency.
4. Wildlife secondary: same constraints for fox/bear/goat/duck; preserve walking, feeding, drinking, standing and sleeping poses.
5. Items: exact 4x4 grid of firewood, stone, ore, clay, fruit basket, fish, bread, cooked meat, axe, pickaxe, hammer, fishing rod, rope, planks, ingots, waterskin; muted natural materials and transparent background.

## Checks
- Godot imports and Web export succeeded.
- Measured 44 object regions are inside their atlas bounds.
- Eight species expose walking, sleeping and drinking mappings. Corrected missing drinking mappings that had fallen back to upright idle; removed a seated fox frame from feeding.
- Wildlife pause/sleep rendering and scenery caching regressions passed.
- Catalog and world screenshots are in client/.agent-qa.
- Short local browser benchmark: Balanced, 48x48 synthetic world, 32 citizens, 16 homes, 240 trees, rain and camera pan; 60 warmup/300 measured frames. Mean 30.0 FPS (capped), median 33.3 ms, p95 33.6 ms, worst 47.5 ms, 71 draw calls. This is not a long-session or live-hosted-world guarantee, nor a controlled causal comparison with yesterday's measurements.
