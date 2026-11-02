# Living Planet — implementation status

The first increment adds checkpointed regional environment state to existing
hydrology/ecology. It does not regenerate existing maps.

Implemented:
- Latitude/elevation cooling and immediately adjacent water moderation.
- Regional labels: highlands, wetlands, coastal and interior.
- Gradual soil moisture, snow accumulation/melt and dry/saturated-soil diagnostics.
- Soil/snow factors affect resource regrowth and farm growth.
- Unused foot traffic decays after a day without use.
- One chunk processed every 12 ticks; duplicate/backward ticks ignored. Per-tile
  elapsed time is bounded to one day to avoid abrupt catch-up jumps.
- Regional diagnostics exposed through the simulation state endpoint.

This is a simplified simulation, not a physically accurate climate model. Warnings
reflect soil conditions, not a flood forecast. Current weather is used for elapsed
updates, not an integrated historical weather series. No terrain conversion or
building removal occurs. Distant chunks update less frequently on larger maps.

Still required for the requested major update:
- Multi-river watersheds, downhill drainage/lakes and coherent mountain/valley redesign.
- Ecology-driven migration and carrying capacity tied to regional food/water.
- Dynamic settlement/trade choices driven by regional identity.
- Regional overlays and visible in-game warning notifications.
- Visual seasonal vegetation/snow integration, long-run balancing and performance tests.

Existing river carving, flooding, regrowth, animal habitats and seasonal behavior
remain in place; they are not all replaced or fully interconnected by this increment.
