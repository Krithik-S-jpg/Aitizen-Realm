# World and player polish

## Changes

- Scale: reduced oversized houses, tents, storage, workbenches, wells, fences and campfires relative to citizens. Existing footprint collision and depth sorting remain authoritative. Existing saves are not relocated.
- Terrain: cached, low-frequency colour variation spans neighboring ground tiles, complementing the existing blended biome edges, shallows and mountain foothills.
- Settlement layout: valid nearby building sites use known settlement proximity as a tie-breaker. Travel distance takes priority: stronger clustering caused a survival regression and was removed. Worn paths connect completed doorways as well as actual roads and avoid blocked cells. Decorative garden borders avoid occupied neighboring ground.
- Lighting: citizens and animals use the same soft ground-shadow direction as scenery. Existing dawn/dusk colour transitions, occupied-home window lights and fueled campfires remain in use.
- Movement: removed idle vertical bobbing so resting feet remain grounded and restrained work bobbing. Existing distance-driven walking and wildlife cycles, stop interpolation, crowd separation, shared meals and social routines are retained.
- Interface: reduced navigation-button height and header spacing. Notification cards support keyboard focus, respect reduced-motion settings and retain danger/warning messages longer.
- Player dashboard: prominent Follow my citizen action, relationship portraits, and account-scoped live avatar, name, activity, memory count and need updates every 15 seconds while visible. Need bars distinguish warning and danger levels. Customization, relationship history and the recorded away timeline remain available. The compact status response is unchanged unless `details=1` is requested.
- Player game projection now includes cave position and preparation fields needed to render citizens inside caves. Private conversations and unrelated metadata remain excluded.

## Checks

- Godot scenery regression check passed.
- Settlement preview rendered and inspected.
- Dashboard JavaScript syntax check passed.
- Six dashboard tests passed, including authentication, account isolation and live need updates.
- Ten interior/storage/settlement checks passed in the initial regression run. The long village scenario initially failed with aggressive clustering; the revised distance-first rule passed its 2,880-tick rerun.
- Web export succeeded.

## Limits

This is an incremental polish pass over the existing systems, not new animation artwork for every action or a regenerated world. Older buildings retain their saved footprints. Decorative paths do not create constructed road resources. Browser-control tools were unavailable for final acceptance, so browser FPS, dashboard visual acceptance and the hosted deployment remain unverified. No guarantee of zero frame drops is made.
