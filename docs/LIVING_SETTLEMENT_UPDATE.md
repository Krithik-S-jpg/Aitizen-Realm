# Living settlement integration

## This update

- Citizens skip resources reserved by other workers. Finishing or interrupting an action releases its harvest claim; inactive workers also release work. At night, work is released for reassignment instead of held indefinitely while sleeping.
- Nearby planned construction is considered before starting another facility of the same type. Existing construction assistance, real inventory transfers, and resource gathering remain authoritative.
- Safe citizens with met needs can take a short evening social break with a nearby neighbour. A completed conversation changes actual social bonds and has a daily cooldown. Survival pressure takes priority.
- Citizens now have a separate 12-frame sleeping atlas. Playback uses the existing 24 Hz animation sampler over a slow 2.4-second breathing cycle, not 24 unique source frames or a stretched idle pose.
- Animal danger and severe thirst interrupt weather/rest routines. Animals reassess a home that no longer matches their habitat before their inactive-period rest.
- The settlement inspector refreshes every three seconds while open, preserves selection, and shows active workers, reasons, carried and communal supplies, monitored shortages, and real construction progress. Facilities within 12 tiles belong to the nearest group for reporting; this is a reporting boundary, not formal territory ownership.

## Verified

The full backend suite passed with 146 tests. The five-citizen acceptance scenario runs 480 ticks without orders or free inventory materials. It asserts all five remain active, all sleep, all travel, multiple citizens complete building actions, and inventories stay within capacity. This is a controlled resource-rich test, not a guarantee for every procedural seed or disaster.

Godot presentation checks verify twelve distinct source cells, transparent edges, animation frame selection, page fit and settlement selection preservation. The sleep sheet was also rendered and visually inspected in Godot.

Existing tree-fall, carrying, gathering contact and staged-building presentation are reused. This update does not replace every action or wildlife animation, introduce rigid-body physics, or fully simulate an economy. Existing two dependency deprecation warnings and the local Godot root-certificate-store warning are separate from these checks.

## Sleep asset provenance

Built-in image generation was used with the existing citizen atlas as an identity/style reference. The original sleep draft was replaced in the renderer by the non-destructive revision `client/assets/pixel_art/citizen_sleep_v2_12f.png`.

Generation specification: new transparent 1536-by-1024 sheet, exactly twelve equally spaced frames in four columns and three rows; same brown-haired, teal-hooded citizen with cream trim, leaf and brown boots; curled asleep on a brown bedroll, head left, feet right, closed eyes; isometric view; six subtle inhale poses followed by six exhale poses; consistent size and baseline; full transparent cell margins; no text, grid, tools or standing poses.

Final edit prompt: Remove the entire dark colored background and all glow. True alpha transparency everywhere outside the twelve citizen/bedroll silhouettes. Preserve the exact canvas, strict four-by-three grid, identities, cell locations, bedrolls and animation poses. Keep only character and bedroll with clean outlined edges. Do not change composition or add anything.

The resulting alpha channel was verified before integration. Generated RGB behind fully transparent pixels is not used as visible background.

The second revision removes the rolled circular bedroll and oversized backpack silhouette, uses a thin rectangular mat, keeps the body long and readable, and is rendered at 64 by 43 pixels so a sleeping citizen never appears larger than the 68-pixel standing character.
