# Deploy Aitizen Observatory on Netlify

This is a separate hosting target. The existing Sites deployment and its data
are not changed. The dashboard UI is shared; Netlify uses its own build,
authentication, Functions API and Blobs store. No Cloudflare account, D1, R2
or ChatGPT service token is needed for this target.

## 1. Import the repository

Push this standalone Aitizen-Observatory repository to your own GitHub/GitLab
repository, then import it into Netlify. Do not use the Sites source remote as
a Netlify Git provider. Do not deploy only the dist folder by drag-and-drop:
this dashboard requires its Functions.

The root netlify.toml sets:
- Base directory: netlify-app
- Build command: npm run build
- Publish directory: netlify-app/dist (Netlify resolves dist relative to base)
- Functions directory: netlify-app/netlify/functions
- Node: 22

Use the Vite framework target, not Next.js or Vinext. Root Sites scripts and
Cloudflare configuration remain for the old hosting target and are not used
by this build. Commit netlify-app/package-lock.json.

## 2. Configure secrets before use

In Netlify environment variables, set these for **Functions** in the production
context. Never use a VITE_ prefix; never commit values or paste them into chat.

| Variable | Purpose |
| --- | --- |
| OBSERVATORY_ADMIN_KEY | Owner sign-in key |
| OBSERVATORY_SESSION_SECRET | Signs the 12-hour HttpOnly session cookie |
| OBSERVATORY_INGEST_TOKEN | Authenticates the game connector |

Use three DIFFERENT cryptographically random values, each at least 32
characters (recommended: 32 random bytes rendered as 64 hex characters).
Generate them in your password manager and keep them there. Do not use a
guessable password. Missing/short/reused keys cause the API to refuse requests.

Redeploy after configuring secrets. Open the HTTPS Netlify URL and sign in
using only the ADMIN key. The upload token cannot read private records and a
browser login cannot upload world data. Sign out clears the cookie; rotating
the SESSION secret revokes existing sessions. No account registration is open.

The static login/dashboard shell can be downloaded publicly, but every data
and picture endpoint requires authentication. This is not Netlify team SSO.
Use Netlify site-wide access protection as an additional layer if desired.

## 3. Point the game connector at Netlify

Leave the game backend and Godot capture integration in Aitizen-Realm.
Start its backend and open your saved world. Run from the game repository:

    backend/.venv/Scripts/python.exe backend/tools/observer_connector.py

At its hidden prompt enter locally (do not commit or share):

    {"provider":"netlify","url":"https://YOUR-SITE.netlify.app","token":"YOUR_INGEST_TOKEN"}

Or set OBSERVATORY_PROVIDER=netlify, OBSERVATORY_SITE_URL and
OBSERVATORY_SERVICE_TOKEN only in the connector process environment.
Use the INGEST token, never the ADMIN or SESSION secret. A custom HTTPS domain
works when provider is explicitly netlify. Redirects are not followed.
Stop the old connector before starting this target to avoid duplicate uploads.

The computer/backend/connector must stay running. Godot supplies viewport
pictures; Ollama supplies optional AI. Hosting does not run your simulation.
Verify Connection, then citizen data, a report, a capture and a chat answer.

## Data and limits

Netlify Blobs persists records across production deploys. Preview deployments
use isolated stores and do not read or prune production observations.
Deploy previews need their own secret values if you want to test them.
Snapshots, reports, questions, alerts and JPEGs use bounded retention, matching
the original dashboard. Question throttling is best-effort for this single-owner
app, not a distributed multi-user quota. Run one connector per target.

Old D1/R2 records are NOT automatically migrated. Export reports/pictures you
need from the old site before retiring it. A new connector upload populates
Netlify with the current snapshot; historical images/reports remain on Sites.
Nothing deletes the old site or changes Supabase saves.

## Local checks

    cd netlify-app
    npm ci
    npm test
    npm run build

For full local Functions + Blobs testing use Netlify Dev from the repository
root, with local secrets kept outside Git. Plain Vite preview only serves the
UI; it is not a replacement for the authenticated Functions API.
A real Netlify deployment still needs an end-to-end check after provisioning.

Official references:
- https://docs.netlify.com/build/functions/overview/
- https://docs.netlify.com/build/data-and-storage/netlify-blobs/
