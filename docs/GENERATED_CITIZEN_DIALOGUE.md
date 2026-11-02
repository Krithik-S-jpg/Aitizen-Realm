# Citizen-to-citizen local dialogue

When OLLAMA_MODEL is configured, ordinary nearby conversations use local Ollama
instead of the rotating topic templates. Each participant receives only their
own needs, activity, remembered places, important memories and recent shared
conversation. The second speaker also sees the first utterance. This is a
two-turn exchange, continued from retained conversation at later meetings.

One background worker runs at most one exchange at a time, with a 15-second
minimum submission interval, finite HTTP timeouts and error backoff. Citizens
continue simulating while it runs. Late replies are discarded after a world
change, more than 90 ticks, separation, sleep or departure from the surface.
No model output executes actions or transfers inventory/knowledge records.
Generated messages appear with a Local LLM label and persist through the normal
message/conversation save data. Prompt grounding reduces but does not eliminate
invented statements; generated dialogue is not authoritative simulation history.

Urgent warnings and real resource handoffs remain factual simulation messages.
With no configured model the existing templates remain available. With a
configured but unavailable model, casual generation fails quietly with a
dialogue_status diagnostic; it does not pretend template speech was generated.

Validation: ten focused tests passed for delivery, malformed output, private
context, departure/world replacement and existing community interactions.
Live inference was not verified because localhost:11434 refused connections.
Start Ollama, then restart the backend and game to use the updated code.
