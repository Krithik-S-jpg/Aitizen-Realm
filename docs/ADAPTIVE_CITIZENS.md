# Adaptive citizens

This extends existing warning conversations, shared jobs, private knowledge and
utility/LLM planning. It does not replace them or modify the Observatory.

## Implemented

- Real completed/failed actions record up to 48 target-specific lessons. Failed
  non-survival targets have bounded cooldowns; urgent survival is never blocked.
- Up to 16 attack memories retain event/source identity. Sharing cannot refresh
  the original observation timestamp. Route costs fade over 960 ticks, separately
  from short-lived fear. Known exploration frontiers consider this evidence.
- Identity-stable ambitions track new mapped tiles, building or foraging skill.
  They add a small utility preference only while healthy, fed and rested. Progress
  is measured from real knowledge/skills, not generated claims.
- Resource advice earns additional directional trust when personally confirmed.
  Missing resources do not imply dishonesty. Verification is bounded/deduplicated.
  Existing gifts and shared work continue to affect cooperation.
- Ambitions and failed attempts become conversation topics; resource sharing,
  delivery and project execution retain existing physical validation.
- Local planner receives ambition, recent outcome and limited danger evidence.
  Citizen profile exposes ambition/progress, actual outcome, confirmed advice and
  existing planner/fallback status. No model reasoning is presented as fact.
- Tight dive return budgets increase a bounded future safety reserve.

All added state uses entity metadata and round-trips through World serialization.
Old worlds require no database migration; fields initialize lazily.

## Validation

From backend: `.venv/Scripts/python.exe -m pytest tests/test_adaptive_learning.py
tests/test_exploration_conversations.py tests/test_community_routines.py
tests/test_wildlife_danger.py tests/test_citizen_planner.py tests/test_decisions.py
tests/test_diving.py tests/test_water_travel.py -q -p no:cacheprovider`

`python -m tools.benchmark_adaptation` runs an isolated 16x16, 50-route benchmark.
It does not measure rendering, a full village, or network/model latency.

## Acceptance still needed

Run a copied saved world with utility and LLM citizens. Observe attack -> spoken
warning -> changed route -> save/load, then resource tip -> travel -> confirmation.
Check profile readability, model availability/fallback and representative large-map
performance. Automated route/save tests do not replace this live acceptance.

This version has three ambition types, not a full evolving life-goal system.
Trust learns from help and confirmed resources; it does not classify arbitrary
generated speech as truth, prove predators remain in place, or model betrayal.
