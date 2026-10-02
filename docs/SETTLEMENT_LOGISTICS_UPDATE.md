# Settlement logistics and households

The living-world simulation now treats a building as a real shared project rather
than an instant recipe purchase.

## Construction flow

1. A citizen chooses a useful structure from current needs and establishes its
   foundation.
2. The foundation records required and delivered materials independently.
3. Citizens gather the missing materials and physically travel beside the site.
4. Each delivery removes material from the carrier's finite inventory and adds it
   to the site ledger.
5. Work cannot start until the site is fully funded.
6. Once supplied, one or more citizens contribute visible work through the normal
   action lifecycle until the building becomes functional.

The older direct placement service is still available to administrator and API
callers. It pays the full recipe immediately, preserving its previous contract.
Autonomous citizens use the staged flow.

## Homes and beds

Completed shelters and tents create households. Shelters hold four residents and
tents hold two. Assignment is deterministic, never exceeds capacity, and records
the citizen's household, home, and bed index. Unassigned citizens remain visibly
homeless and prioritize another shelter or tent. At night, assigned citizens walk
to their own home and bed location before sleeping.

## Settlement work board

Every settlement exposes live requests derived from world state:

- missing construction materials;
- funded construction waiting for workers;
- campfires that need fuel;
- farms with food ready to harvest.

Requests have priorities, reasons, targets, and claim state. A current action is
matched to the relevant request, and stale claims are released automatically.
The settlement inspector displays real households, bed availability, carried and
stored supplies, shortages, current citizen activities and reasons, open work,
and construction funding/progress. No display totals are fabricated by the UI.

## Acceptance coverage

Automated coverage proves that:

- construction is blocked until its materials arrive;
- two citizens can fund the same site through separate deliveries;
- material is conserved between packs and foundations;
- bed occupancy never exceeds building capacity;
- overflow citizens move into a second home;
- job-board requests change from delivery to building after funding;
- five autonomous citizens move, sleep, deliver supplies, collaborate, and finish
  a functioning camp structure without direct orders.
