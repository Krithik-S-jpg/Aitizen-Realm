# Living Village: first implementation

## Multiple local-LLM citizens

Select each citizen in Citizens, then choose **Use Local LLM + fallback**. Changing
one citizen no longer changes anybody else's mode. Modes persist in checkpoints.
One inference worker serves a FIFO queue of up to 16 pending citizen observations;
Utility AI handles all waiting citizens and urgent survival. Responses are matched
to citizen identity and rejected when the world, position, or tick window is stale.
This is not simultaneous inference and does not guarantee every request is used.

## Connected village systems

- Households prefer existing home assignments and nearby homes. Residents can use
  finite home stockpiles through real deposit/withdraw trips. Capacity is 50 units;
  older overfilled saves retain their contents rather than deleting them.
- Adjacent safe citizens can barter one unit for one unit when their known
  construction shortages complement their spare materials. No currency is created.
- Seasonal reserve targets are four food units per resident, eight in autumn/winter.
  A shortage raises gathering priority and encourages actual food deposits.
- Daily fractional spoilage removes 3% of carried perishables and 1% in village
  stockpiles. It is a simple quantity model, not individual item expiry dates.
- Completed buildings slowly lose condition; strong wet weather accelerates wear.
  Safe idle citizens beside a known worn building can spend one wood to repair it.
  No building collapse is enabled. Condition and a daily story are inspectable.
- Injured idle citizens recover gradually when fed, hydrated, and out of danger.
  This is basic recovery, not a full medical-treatment system.
- Settlements show real food reserves, maintenance needs, and a bounded story log.

All new state uses existing world checkpoint serialization; old saves receive
default values. No hosted schema changes were made.

## Still to build and validate

Neighbours can now propose an existing unfinished site, relay its location, and
endorse the project. An active-member majority raises its construction priority;
real completion updates the story. This is deterministic agreement, not an LLM
debate or unrestricted project generation.

Repair and first-aid jobs now claim a target and travel using known routes. Repairs
consume wood; first aid consumes fiber and has a per-patient cooldown. Survival
interrupts both. Long-distance barter contracts, a richer medical system, and
destructive storm consequences remain future work. Existing
fishing, cooking, farming, job claims, and sleep routines remain active.

The five-citizen fixture now runs 2,880 ticks (120 days at the default clock),
including winter, with upkeep and communication enabled. It exposed a boat return
anchoring bug, now fixed. This is a small provisioned test map, not proof that all
generated worlds or populations survive. Two queued citizens also received real
Ollama proposals; isolated real-model food and construction tests passed.

Automated tests cover mode independence, response ownership, stale world rejection,
atomic barter, daily spoilage idempotency, repair costs, and survival-priority recovery.
Live multi-citizen Ollama throughput and large-population rendering FPS need separate
measurement; passing mocked planner tests does not establish inference performance.
