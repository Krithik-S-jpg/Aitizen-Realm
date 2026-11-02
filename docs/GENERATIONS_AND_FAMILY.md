# Generations and family life — initial implementation

New-world clock default: 1800 ticks/day (30 minutes at 1 tick/second).
Existing saves retain their calendar settings; choose 1800 in Settings to slow
their days. Movement and animation timing are unchanged. Biological aging is a
separate days-per-world-day setting: 1 is calendar aging, 0 freezes aging,
365 compresses a year into one world day. Pregnancy uses biological days too.

Stages: infant <1 year, toddler <4, child <13, teen <18, adult <60, elder 60+.
Births are opt-in in Settings and labeled experimental while care and animations
remain incomplete. Do not enable on an irreplaceable world; use a copied save.
Adult legacy citizens retain their age. Aging records its last tick to prevent
duplicate increments, and newborn IDs are fixed at conception to prevent replay
births. State is serialized with normal world saves.

Compatible nearby adults with reciprocal trust/familiarity and family preferences
may partner in a shared completed home. Pregnancy requires a female/male adult
pair, spare bed capacity, good health and carried food reserves. Preferences
default deterministically by identity and can be overridden in metadata with
`wants_children`. This is an abstract simulation, not a medical model.

Pregnancy lasts 280 biological days, followed by recovery and a birth spacing
cooldown. Nearby parents or adult household members can supervise/feed children;
feeding consumes inventory. Guardians can interrupt optional work and navigate
back to a hungry child. Children learn bounded skills from nearby adults.
Minors cannot independently hunt, dive, enter caves or join expeditions.

Profiles show family and age information and a connected Family tree view.
World sprites normalize adult standing height to 48px independently of portraits.
Initial atlas covers swaddled infants, male/female toddlers and children and male
elders. Frame cropping is cached; no per-frame image decoding.

Artwork: built-in image generation, followed by transparent-background edit.
Saved asset: client/assets/pixel_art/family_stages_v1.png.
Prompt: 4 columns of motion frames x 6 age rows; medieval pixel-art infant,
male/female toddler, male/female child, male elder; full figures, transparent
gutters, consistent ground alignment. The second pass requested removal of all
background while preserving figures. Alpha was checked before integration.

## Not complete yet

Dedicated teens/female elders, complete feeding/crawling/carrying/teaching/rest
animations, guardian carrying and supervised movement, family preference UI,
elder work adaptation, proactive
water provisioning, long-run balance and live visual acceptance remain pending.
Current young citizens stay near their birth position; this is not a finished
childhood simulation. The entire asset set must not be described as complete.

Validation: tests/test_families.py, test_calendar.py, test_decisions.py,
test_diving.py, test_community_routines.py, test_identity_hunting.py;
Godot tools/TestFamilies.gd and tools/TestCitizenProfile.gd.
