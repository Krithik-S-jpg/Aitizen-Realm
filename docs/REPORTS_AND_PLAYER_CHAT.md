# Reports, player chat and notifications

- Open History (or any observatory page), refresh, then **Report / download**.
  The report is a frozen snapshot of retained events and economy, not a complete
  lifetime archive. Choose a destination using **Download report (.txt)**.
- Open a citizen profile, **Actions & communication → Talk to this citizen**.
  Ollama supplies bounded English dialogue when configured. Replies identify
  local-model generation versus factual simulation-status fallback. Chat does
  not execute commands. The last 40 messages are included in normal world saves.
  A world change while a response is pending rejects that response.
- Significant events slide in at bottom left and expire after five seconds.
  Newer cards replace older ones, pages no longer cover the overlay, and event
  cursors reset on world creation/load. Routine sleep/wake remains in history.
- The citizen profile identity column scrolls on short windows to avoid clipping.

Validation covers fallback chat without state mutation, report generation,
profile bars, and notification filtering/deduplication/five-second expiry.
Live model dialogue and every possible display resolution are not covered by
these automated checks. Chat output is generated text, not evidence of actions.
