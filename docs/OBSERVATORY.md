# Private Aitizen Observatory

The standalone sibling repository `../Aitizen-Observatory/` is a private Sites/Vinext dashboard, with D1 for
monitoring records and R2 for JPEG game captures. This is separate from Supabase
world saves: it never changes saves, citizens, goals or simulation settings.

## Data flow

Godot (game viewport only) → local FastAPI observer feed → outbound connector →
private hosted dashboard. No inbound public access to the local backend is needed.
Only run the site owner-private: its ingest endpoint relies on Sites dispatch's
service-bearer protection and explicitly rejects browser-session uploads.

Start the backend normally. Start the updated Godot client for pictures.
Run `backend/.venv/Scripts/python.exe backend/tools/observer_connector.py` from
the repository root. The hidden prompt accepts `url` and `token` as a JSON object;
use the site's service-access credential through trusted tooling, not a public
browser page. Alternatively configure `OBSERVATORY_SITE_URL` and
`OBSERVATORY_SERVICE_TOKEN` in the connector process environment. Never commit
or paste the token into website code. The current connector keeps it in memory;
it needs to be supplied again after that process stops. No OS auto-start is set.

Snapshots publish approximately every 15 seconds (model requests may extend a
cycle). Reports publish every five minutes. The backend's 90-second connector
lease enables game viewport uploads every 45 seconds. Stopping the connector
automatically disables capture after that lease expires. No desktop or other-app
screenshots are taken. The backend stores the latest JPEG in memory only.

## Features and limits

- Overview, population/resources charts, scenarios, inventories, buildings.
- Citizen needs, current reasons, significant memories and recent conversations.
- Deduplicated recorded alerts, dated screenshots, location map.
- Local Ollama reports and queued questions; model-free factual fallback is labelled.
- Download observations, text reports and JPEGs from the website.
- The last received data remains available offline, with a stale-feed warning.

The connector uses the backend's `OLLAMA_MODEL`; no new paid model service is
required. It supplies bounded observations as untrusted data with no action tools.
Generated interpretations are labelled; all factual panels are simulation data.
Questions expire after 15 minutes without a connector and are limited to 20/hour.
Retention is bounded: latest snapshot with 120 metric samples, 96 reports,
500 alert records (200 displayed), 24 captures and 100 questions (30 displayed).
Snapshots include up to 500 citizens/buildings and 80 conversations; important
memories are capped at eight per citizen. This is an observer, not a full replay
archive. Export important reports before retention removes them.

Your PC must run the backend and connector for fresh observations. Godot must
also run for new pictures. Hosting does not move the simulation to the cloud.
Neither the connector nor opening the website starts a simulation automatically.

## Development

For Netlify hosting, follow the standalone website's `NETLIFY.md`. The connector
accepts `provider: "netlify"` with a Netlify HTTPS origin (or explicit custom
domain) and the website's `OBSERVATORY_INGEST_TOKEN`. It sends a standard Bearer
header; the existing Sites mode is preserved. Environment configuration also
supports `OBSERVATORY_PROVIDER=netlify`. Do not reuse the Sites service token.

Website files and their existing Git history live in
`H:\F Proj\Aitizen Realm\Aitizen-Observatory`, outside this game repository.
Only the game-side projection/API, connector, viewport capture and their tests
remain here. They communicate with the hosted URL, not the website's local path.
The website's README documents its independent development commands.

Follow the Sites skill for installation/build/publishing. The source manifest
retains the Site ID and DB/BUCKET bindings. Schema migrations live in `drizzle/`.
Type-check with the local TypeScript executable. Backend projection/access tests
are in `backend/tests/test_observer.py`. Do not commit credentials, `.wrangler/`
data or development uploads. Hosted access must stay owner-private.
