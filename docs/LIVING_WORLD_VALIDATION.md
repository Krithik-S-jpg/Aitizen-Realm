# Living-world interaction verification

## Sheltered sleep and personal danger memories

- Sleeping citizens are hidden only when their completed, assigned residence is valid and they have reached its entrance. Outdoor sleepers remain visible. Valid indoor sleepers are excluded from wildlife attacks.
- Hungry adult wolves pursue citizens; nearby adult bears and boars can attack defensively. Damage requires reaching the target and respects a four-tick attack cooldown.
- Victims and awake, nearby witnesses with visibility record separate danger episodes. Fear decays with time; a recent attack-location warning influences safety decisions. Personal episodes survive world snapshot serialization.
- Citizens page: select a citizen, then choose **Memory tree / Fear…** to inspect a connected-node graph of recorded experiences, participants, emotional effects and associated decisions. Supports node dragging, pan, zoom and minimap navigation; connections cannot be edited. Reopen it after refreshing citizens to inspect updated memories. Graph creation and rebuilding tests passed; the rendered graph was captured and visually checked.
- Carrying uses stone/basket artwork instead of primitive cargo polygons. Small food quantities remain in the pack; gathering feedback travels from the resource toward the citizen, and working citizens face their target.
- Verification: 163 backend tests passed; the final focused rerun passed 7 tests. Godot memory/sleep visibility, interaction effects and reference-page checks passed headlessly. No new animation sprite sheets were generated in this pass.

## Implemented in this pass

- Registered citizens must reach a resource before gathering it; standing trees must be chopped before timber can be collected.
- Adjacent chopping/gathering uses the interaction animation instead of incorrectly appearing idle.
- Depleted resources (quantity zero) survive snapshot validation. Entity tags serialize in stable order.
- Observer feeds share action, target, remaining route, decision reason and indoor-rest metadata.
- Night routines report their assigned shelter and avoid blocked entrance positions.
- Animal decisions expose reasons and movement targets. Ducks displaced inland seek nearby water even without thirst; danger still takes priority.
- Citizen/animal inspection displays route length, target and decision explanation.

## Verification

- Backend: 156 tests passed (two dependency deprecation warnings).
- Added a tree -> fallen log -> collection -> save/load -> storage -> delivery -> completed shelter regression, including rejection of distant gathering and direct tree harvesting.
- Added route/sleep observer and displaced-duck habitat regressions.
- Godot: TestCitizenActionFrames, TestInteractionEffects and TestSettlementPresentation passed headlessly.
- Editor import completed without script parse errors. Sandbox certificate-store and editor-settings-write warnings remain environmental limitations of that run.

## Follow-up: settings and character artwork

- Eight identity-specific action sheets are now connected to both the renderer and appearance selector. Rowan has a separate gathering supplement. Frame rectangles are baked from transparent gaps and connected silhouettes to exclude neighboring tool fragments. Original images are not modified.
- Each identity has eight actions with six source poses each. Playback is sampled at 24 Hz, not 24 unique source drawings per action. See `client/assets/pixel_art/citizens/GENERATED_ACTIONS.md` for prompts and asset paths.
- Settings supports an authenticated connection check, pause, named Supabase save, latest-50 save list and confirmed restore with world reload. Admin tokens stay in session memory; Supabase keys stay backend-only.
- Full backend suite: 157 passed. Godot checkpoint controls, catalog bounds/transparency checks and responsive page checks passed. Gallery and settings captures were visually inspected.
- Hardware benchmark: Intel UHD Graphics / Vulkan, dense 64x64 fixture, 520 resources and 48 mixed citizens/animals: 60.0 average FPS (16.67 ms/frame), reported process 14.16 ms and 127 draw calls. This is not a guarantee for arbitrary populations or world sizes.
- Hosted checkpoint-table read reached Supabase but returned HTTP 401 Unauthorized. Credentials are configured, but hosted save/restore is NOT verified. Check the server secret and matching project URL in the ignored backend environment, then restart the backend. No hosted data was changed by the read-only verification.
