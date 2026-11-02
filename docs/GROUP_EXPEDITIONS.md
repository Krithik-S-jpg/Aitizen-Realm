# Expeditions and shared knowledge

Healthy, idle, nearby autonomous citizens with two carried food units can agree
to a short frontier survey. No supplies are created. One party of two is active
at a time; route length is capped and navigation uses each citizen's knowledge.
The trip returns before depleted reserves or darkness. Urgent danger/death,
unreachable routes and conflicting activities release citizens to survival AI.
Companions separated by more than six tiles turn back to their departure points.

Discoveries come from actual perception along the route. Returning explorers
share up to 25 new resource locations with nearby awake nonmembers, retaining
source, observation date and reduced confidence. A significant discovery memory
records the expedition. Limited adjacent first aid consumes one fiber for five
health, once per trip.

World.expeditions persists up to 40 ledger entries through ordinary world
serialization. Older worlds default to an empty ledger. No hosted SQL migration
is needed for the checkpoint payload. Hosted save/load was not tested here.

Open Research or History, then **Expeditions** in the sidebar to inspect parties,
stages, destinations, supplies, discoveries and delivered report counts.

## Extended party stages

Local-LLM members request an asynchronous Ollama itinerary choice from known
survey, cave and shore candidates. Invalid responses, outages and an eight-tick
deadline fall back to utility selection. Replacing the world invalidates pending
responses. Model output cannot grant supplies or execute unvalidated movement.

Preparation obtains one fiber per citizen for first aid. Boat parties also need
one boat each. Citizens use known storage, reserved harvesting jobs and ordinary
crafting recipes. Missing sources or expired preparation budgets abort the trip.

Cave parties enter the same known cave, traverse its connected passages and
return through the entrance. Low reserves shorten the return route. Boat parties
use two single-seat vessels and the existing rowing/diving/return routine.

Healthy companions can retrieve nearby overland casualties: walk to the patient,
pick them up, then carry them along a known land route to the departure point.
Transport costs extra energy and survives serialization. It does not heal or
resurrect the patient. Immediate threats override rescue. Carried citizens are
hidden as independent sprites; the carrier composites the patient's actual
appearance into a four-pose carry/tow cycle, with a RESCUE cue.

The expedition inspector also exposes planner, itinerary, missing equipment and
retrieval status. Automated tests cover equipment gathering, cave and boat trips,
casualty pickup/save/load, first aid, and stale planner fallback.

## Overnight travel and interior rescue

Two-day surveys are offered when both citizens carry at least eight food units
and know a reachable freshwater-side campsite. They physically reach camp, eat
from inventory, drink beside water, rest overnight, and attempt a second-day
survey before returning. Insufficient camp reserves force an early return.
Camp stage, observed night and return budget persist through save/load.

Nearby companions in the same cave can reach an injured citizen along connected
passages, carry them to the entrance, then continue the overland retrieval.
Underwater companions can tow a casualty to a known shore only when the helper's
oxygen and stamina cover approach plus return with a margin. Movement is one
tile per tick; oxygen is consumed and depleted oxygen can damage the casualty.
Rescue control suppresses independent movement until extraction or interruption.
Interrupted rescue restores self-return routes and clears carrying flags.

Verification: full backend suite 235 passed, 3 optional tests skipped; targeted
overnight/rescue tests include real needs advancement, camp reload and mid-tow
reload. Godot rendered carry/tow scenes for Rowan, Juniper and classic avatars;
screenshots are in client/.agent-qa/rescue-carry.png and rescue-tow.png.

Limits: two-day land surveys, not indefinite or multi-day ocean voyages; nearby
party rescue, not remote search-and-rescue dispatch. No multi-seat boats. Carry
animation is code-composited from existing character assets, not a new painted
sprite atlas. Long-running acceptance in the user's saved world was not performed.
A live qwen2.5:1.5b itinerary response passed schema/choice validation. Full-game
LLM acceptance and hosted Supabase save/load have not been verified here.
