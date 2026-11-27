# Illustrated terrain kit

Asset: `client/assets/world/cohesive/terrain-kit-v2.png`. Built-in image generation, followed by a transparent-background edit. Six cells in a 3 by 2 atlas: concave corner, convex corner, ramp, broad waterfall, tall waterfall, rocky foothill. Runtime selects exposed edges and draws the art beneath terrain caps. Performance quality retains procedural geometry. Existing terrain navigation is unchanged.

Final generation prompt: Production game sprite atlas, transparent background, 3 columns by 2 rows of six separate isolated modular terrain props, equal cells and generous transparent margins, no text. Detailed naturalistic pixel art matching medieval isometric simulation: muted warm gray limestone, olive grass, moss, consistent upper-left sunlight, orthographic 2:1 perspective. Concave and convex grassy cliff corners, ascending grass/gravel ramp, broad short and narrow tall waterfalls with foam, rocky mossy foothill. Coherent scale, crisp textured stone, clean alpha edges.

Final edit prompt: Remove all background to actual transparent alpha around and between objects; preserve all six objects, positions, detail, colours and 3-column 2-row layout. No backdrop, haze, outside ground plane or floating shadows. Preserve terrain pieces.

World palette uses a small shared RGB modulation without replacing terrain shaders. Buildings, resources, wildlife, characters and interiors keep their existing illustration and animation sheets; this is a cohesion pass, not a complete redraw of every frame. Atlas catalog validation checks image bounds. UI portraits stay independent.

Measured desktop GL Compatibility stress fixture: 46.9 FPS, median 19.36 ms, p95 34.08 ms, worst 75.86 ms, 186 draw calls. This misses the benchmark target and is not hosted FPS. Hosted diagnostic navigation redirected to /account and needs user sign-in. The browser diagnostic now includes elevated terraces.
