# Aitizen Realm implementation roadmap

This is the accepted eleven-phase direction. Existing systems are extended rather than recreated. Source presence is not a claim of complete acceptance or visual quality. See PLATFORM_AUDIT.md for known reliability gaps.

| Phase | Existing foundation | Outstanding acceptance / work |
| --- | --- | --- |
| 1 Core | FastAPI services and domain interfaces; Godot custom Node2D renderer; REST/WebSocket; calendar; Supabase checkpoint/archive adapters; paused checkpoint restore API | Hosted database verification; automatic client refresh after restore; coherent tick publication; scheduler/analytics checkpointing; architecture cleanup. A TileMapLayer conversion needs measured justification. |
| 2 World | Seeded terrain, biomes, water terrain, climate/weather/day/night/seasons, resources, plants/wildlife | Connected river/lake hydrology, ecological continuity, visual biome transitions and long-run tests |
| 3 Citizens | Entities, names, age, health/needs, skills, inventory, goals, perception/private knowledge | Personality affecting decisions, complete citizen lifecycle and consistent biological clock |
| 4 AURELIA | Utility selection, actions/goals, navigation, memory, decision reasons | Persistent long-term plans, detailed competing-motive explanations, resource-to-building acceptance |
| 5 Social | Communication, trust, groups, professions, skills; animal family/lifecycle | Citizen families/reproduction, reputation, education and inheritance |
| 6 Civilization | Construction, housing types, farms, crafting, shared storage, basic groups | Businesses, markets, trade/economy, settlements as distinct entities, roads and citizen migration |
| 7 Advanced society | Limited individual knowledge and experimental records | Technology discovery, culture, language, beliefs, laws, governance, diplomacy, conflict/military |
| 8 Living world | Finite resources/regrowth, grazing, predation, needs affected by climate | Disasters, disease transmission/treatment, measured civilization-environment feedback |
| 9 Research | Events, memories, metric export, experiment records, explicit Supabase archive | Life-story presentation, historical map/replay, causality, parallel runs, counterfactuals/comparison |
| 10 Observatory | World/citizen/build/research/history/settings navigation; inspector, minimap, notifications, effects | Full responsive visual acceptance, settlement/economy modes with real data, richer source animation frames |
| 11 Quality | Backend tests, headless Godot checks, preview/benchmark tools, logging and restricted database endpoints | Docker, CI, integrated performance budgets, full authorization review and long-running failure tests |

## Current delivery: checkpoint restore

`POST /api/v1/checkpoints/{id}/restore` uses the existing admin token and Supabase store. It validates the stored version, tick, world, calendar and tick rate, rejects a running/in-flight simulation and pending scheduler tasks, then installs the state paused. Invalid payloads do not replace the world. Research observations from the former timeline are cleared because v1 checkpoints do not contain analytics history.

Use the Godot Reload World control after restoring, then resume. Hosted Supabase connectivity is not established by mocked API tests. No new cloud migration is required for restoring existing version-1 checkpoints.

Next gates: automatic restore notifications/client cache reset, clock consistency across lifecycles, full save/load UI, and construction acceptance. Later phases remain on this roadmap rather than being represented as implemented.
