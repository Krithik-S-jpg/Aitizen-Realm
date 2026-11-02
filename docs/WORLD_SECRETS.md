# The world has secrets

Seeded worlds now contain an initial three-place archaeology trail: a waystone,
a ruined watchtower and an abandoned settlement. Locations are on one connected
walkable land component and avoid occupied resource/building cells. Small worlds
without enough room may contain no trail. Culture, departure cause, age and site
locations are deterministic for a world seed; saved facts are never regenerated.

Citizens spot sites within perception range but inspect inscriptions only within
one tile. Each citizen has private discovery records with confidence and source.
A clue can identify a distant location, but navigation still travels through
known terrain, extending knowledge through actual perception. Healthy citizens
can pursue leads alone or through the existing two-citizen expedition system.

Persistent curiosity preferences cover history, geography, wildlife and unusual
terrain. These bias exploration, not permanent professions or mandatory jobs.
Survival and actual route feasibility still take priority.

Local conversations transfer only selected, personally known records. Ollama's
context includes private evidence and preferences, not hidden world history.
Generated comments are stored separately as interpretations, never used to
rewrite evidence or create artifacts. Utility dialogue provides a fallback when
no model is configured. Prompt instructions cannot guarantee every generated
sentence is factually correct; the journal labels interpretations explicitly.

Open Research or History → Discovery journal. It contains observed sites, map
links, procedural field sketches, artifact descriptions, discoverers, confidence,
expedition references and interpretations. Double-click a row to focus a site.
Undiscovered sites are excluded from journal export. Examining an artifact does
not add an item to inventory; portable artifact collection is not implemented.

World truth and personal records are included in existing World checkpoint
serialization. Older saves default to empty fields and initialize on observation.
No hosted schema migration is required. Hosted Supabase roundtrips and a long
live play session have not been verified for this update.

Checks include seed reproducibility, save/load, proximity-gated evidence, sharing
provenance, private LLM context, physical clue-trail navigation, and protection of
facts from generated interpretations. Godot preview: TestDiscoveryJournal.gd.
This is one seeded mystery chain per eligible world, not an unlimited quest generator.
