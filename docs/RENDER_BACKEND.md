# Render backend demo

Deploy the repository's render.yaml using Render **New > Blueprint**, connecting
Krithik-S-jpg/Aitizen-Realm and the branch containing these changes. Confirm the
Free plan. No payment or deployment is performed by adding this file.

Render generates HOSTED_ADMIN_TOKEN. Keep it server-side; do not put it in a
Godot export, browser JavaScript, Git, or URLs. The hosted entry point refuses
startup without a token of at least 32 characters. /healthz is public; every
other HTTP route and WebSocket handshake requires Authorization: Bearer TOKEN.
The ordinary local app.main and app.browser_demo entry points are unchanged.

This is backend staging, not a playable public browser deployment yet. Open
the service root to sign in using HOSTED_ADMIN_TOKEN from Render's Environment
settings. Enter it only on the HTTPS sign-in page. A signed, Secure, HttpOnly,
SameSite=Strict cookie expires after 12 hours; the owner token is not stored in
the cookie. Logout clears it. Rotating the token invalidates existing sessions.
Cookie-authenticated mutations and WebSockets require a matching HTTPS Origin.
Bearer authentication remains supported for trusted server clients.
The game must be served on this same origin to use the browser session; a game
on a different host is not connected by this change. Local HTTP demos still use
app.browser_demo and do not use these HTTPS-only cookies.

Use one worker only: this simulation stores its active world in process memory.
Free Render services sleep after idle periods and lose local disk contents on
restart. Save worlds to configured Supabase checkpoints explicitly before a
restart. Automatic durable cloud recovery is not implemented by this blueprint.
Do not treat LOCAL_RECOVERY_PATH on Render's free filesystem as durable storage.

OLLAMA_MODEL is empty initially: utility AI is the deployment baseline. The
existing direct localhost Ollama calls cannot reach the owner's computer from
Render. The outbound local worker, authenticated task queue, expiry handling,
and result validation remain a separate required milestone. Never expose port
11434 to make those existing calls work remotely.

After deployment, verify /healthz returns 200, unauthenticated /api/v1/simulation/state
returns 401, and a request with the owner bearer token returns 200. Do not log
the token. Hosting success alone does not verify browser play or remote AI.
