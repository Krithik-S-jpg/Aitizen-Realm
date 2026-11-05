# Browser hosting trial

The Web export preset is single-threaded and uses Compatibility rendering only
on web. Native desktop rendering is unchanged. JSON catalogs are included;
test tools and QA screenshots are excluded. Build output is ignored under
`.local-build/web`.

Browser endpoint selection:
- `window.AITIZEN_API_ORIGIN` before Godot starts, if configured by the host;
- otherwise the website's own origin (requires an API reverse proxy).
- Native desktop still uses `client/config/runtime.json`.

The backend must serve HTTPS/WSS. For a separate API origin, allow only the
actual game origin in CORS. Do not expose the current admin/destructive API
publicly until authorization is enforced. Never embed admin, ingest, database
service or session signing secrets in HTML, JS, JSON, or the Godot pack.

Export command after installing matching Godot 4.7 export templates:

```powershell
& 'H:/Godot_v4.7-stable_win64.exe/Godot_v4.7-stable_win64_console.exe' --headless --path client --export-release Web
```

Before deployment verify the output pack/WASM sizes against the chosen host's
per-file limits, successful browser startup, asset imports, API/WebSocket access,
and account authorization. The static client alone is not a hosted simulation.

The official 4.7 template archive was downloaded and its single-threaded web
templates extracted into `.local-build`. The preset uses these local custom
template paths. Script warning audit: zero failures.

Release export generated `index.html`, JavaScript, `index.pck` (78,951,416 bytes)
and `index.wasm` (39,509,339 bytes). Both large files exceed Cloudflare Pages'
25 MiB per-file limit. Hosting there requires an asset delivery/repacking plan;
do not assume the export can be uploaded unchanged. Browser runtime testing is
still pending; export success is not proof of a playable browser session.

## Private local demo

The opt-in `app.browser_demo:app` entry point serves the exported game at
`/game/` alongside the existing API and WebSocket routes. Start it from backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.browser_demo:app --host 127.0.0.1 --port 8000
```

Run only one backend on this port. Keep Ollama on localhost:11434. Start the
downloaded Cloudflare tool from the repository root with an explicit owner email:

```powershell
.\.local-build\cloudflared.exe tunnel --url http://127.0.0.1:8000 --allowed-mail YOUR_EMAIL --no-autoupdate
```

Never omit `--allowed-mail`: the simulation API does not yet implement player
authorization. Open the printed HTTPS URL with `/game/` appended and complete
the email PIN prompt. The URL changes on restart, and the computer, backend,
Ollama and tunnel must remain running. This is a private demo, not production.

Verified locally: game HTML and simulation state return HTTP 200; Ollama lists
qwen2.5:1.5b. Verified through the protected tunnel: unauthenticated game, API
and WebSocket-path HTTP requests redirect to the Cloudflare login page.
Authenticated browser rendering and live WebSocket play still require the
owner to complete email verification. Model availability alone does not prove
citizen inference is working end to end.
