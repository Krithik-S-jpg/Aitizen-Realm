# Optional LLM citizen pilot — initial integration

## In-game switching

Citizens page -> select citizen -> Use Utility AI / Use Local LLM + fallback.
Mode persists in world saves. Selecting a pilot resets other citizens to utility
mode. A mode change invalidates a pending proposal without cancelling physical
work already underway. Planner status appears in the citizen details.

## Live smoke scenarios

Set AITIZEN_LIVE_LLM_TEST=1 and run pytest tests/test_llm_gameplay.py.
These are isolated simulation-engine integration checks with real local Ollama,
not a full visual or long-running gameplay evaluation. Food and construction
materials are supplied by the test fixture; the model is offered a single goal
to test execution wiring. Autonomous gathering, unconstrained choices, shelter
routines, threats, long-run survival and rendered animations need separate trials.

Disabled by default. Install the backend `llm` optional dependency (LangGraph)
using your package manager, run Ollama locally, and configure backend/.env:

```
LLM_CITIZEN_ID=<one existing citizen UUID>
OLLAMA_MODEL=<an installed local model name>
```

Restart the backend. No cloud model or database changes are involved.
This first slice chooses a goal, not arbitrary actions or coordinates. Existing
backend logic resolves known targets, validates paths, reserves resources and
executes actions. Urgent utility motives cannot be demoted. Night routines and
danger interrupts remain deterministic. No fixed professions are assigned.

One background worker, at most one pending request, 15-second submission cooldown,
45-second response timeout (3-second connection timeout), bounded generation and important personal memories only.
Utility AI continues while thinking. World identity, citizen, position and tick
age are checked before accepting a response. Pending workflows are not saved;
loaded worlds discard old proposals. Proposal/status/executed goal are stored in
citizen metadata, separately from the existing action outcome history.

This is not the full milestone yet: hardware/model benchmarking, live Ollama
survival/construction trials, replay datasets and a dedicated inspector panel
remain. CrewAI and multi-citizen coordination are deliberately not enabled.
