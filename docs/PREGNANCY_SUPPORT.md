# Pregnancy and family support (experimental)

Existing conception requires the experimental births setting, adult unrelated
partners who want children, a shared home with room and food reserves, and good
health/needs. Pregnancy is non-graphic and uses biological days, independently of
movement speed. This is a game model, not medical advice or a medical simulation.

Added in this pass:
- Progress, trimester, days remaining, food/water/rest/help warnings.
- Small prenatal hunger/thirst increments guarded against duplicate ticks.
- 42 biological days of postpartum light duties, shown in the citizen profile.
- Hunting, diving and new group expeditions blocked during pregnancy/recovery;
  earlier rest priorities. Existing expeditions are not automatically recalled.
- Guardians fetch finite food/water from their own household stockpile through
  normal navigation and consume actual supplies. No supplies are invented.
- Tests cover progress, duplicate updates, activity guards and conservation of
  household resources; existing birth/save-load tests remain in test_families.py.

Still required: safe-home birth routing, support-person coordination, personal
family-preference UI, full existing-trip recall, safe supervised child movement,
water collection when no household stock exists, and live saved-world acceptance.

## Art draft

`art/aster-care-draft.png` was generated with the built-in image tool, using
`scout_human_v2.png` as identity/style reference. Alpha spot checks confirmed
transparent gutters despite the preview backdrop. The project copy is
`client/assets/pixel_art/citizens/aster_care_v1.png`. Aster teaching uses its new
four-frame row. Carry/cradle frames are registered, but infant transport behavior
is not yet connected. Other appearances do not reuse Aster's identity.

Prompt: A four-column, three-row transparent sheet matching adult Aster's brown
hair, teal tunic, brown trousers/boots and human proportions. Four infant-carry
walking frames, four gentle cradling frames, four open-book teaching gestures.
Consistent scale/feet, generous gutters, no labels or background.
Correction: remove brown/black background and glow; preserve characters, poses,
layout and size, output genuine alpha transparency.

Dedicated age/work/carry art, hunting cleanup, LLM-load/FPS benchmarks and live
backend-restart tests are not completed by this change.
