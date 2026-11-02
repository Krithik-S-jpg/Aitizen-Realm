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

Current blocker: the owner has no server account yet, so no authenticated public
backend origin exists. No production deployment is claimed. Account creation and
provider identity/payment verification must be completed by the owner.
