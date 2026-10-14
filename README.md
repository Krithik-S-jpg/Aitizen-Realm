# Aitizen Observatory

## Netlify deployment

See [NETLIFY.md](NETLIFY.md). The root `netlify.toml` selects the independent
`netlify-app/` build with Netlify Functions, Blobs storage and owner-key login.
The existing Sites target described below is retained, but is not used by Netlify.

Standalone, owner-private monitoring website for Aitizen Realm. This repository
has its own Git history and Sites deployment. It is not a game subproject.

Live site: https://aitizen-observatory.good-pin-6185.chatgpt.site

## Develop

Use Node 22.13 or later. Run `npm run install:ci` for a clean installation,
then `npm run dev`. Type-check with `npx tsc --noEmit`; build with `npm run build`.
On Windows, if the npm shim fails, invoke the installed npm CLI with Node.
Follow the Sites workflow for source synchronization and private deployment.

## Repository layout

- `app/observatory.tsx`: dashboard pages and live interaction state.
- `app/globals.css`: responsive dashboard design, motion and accessibility.
- `components/observer-widgets.tsx`: reusable charts, position map and empty states.
- `lib/observer.ts`: monitoring contract, labels and export helpers.
- `app/api/observer/`: authenticated reads, service uploads and question queue.
- `app/api/picture/`: private image delivery.
- `db/` and `drizzle/`: storage schema and versioned migrations.
- `.openai/hosting.json`: existing Site identity and D1/R2 bindings.

The game repository retains the FastAPI projection, outbound Python connector,
Godot viewport capture and their tests. Communication is HTTP only; this site
does not import files from the game. Moving this checkout does not require a
database migration or a different hosted URL.

## Security and operation

Keep the existing Site owner-private. The ingest endpoint relies on private
Sites service authentication and rejects browser-session uploads. Never commit
service tokens, local databases, runtime credentials or generated archives.
No browser controls can change the world. Preserve the existing access policy.

Your PC/backend/connector must run for new observations; Godot must run for
pictures, and Ollama for local AI. There is no automatic startup service.
The Connection page explains freshness and capture status. Offline data is
clearly marked; reports and pictures can be downloaded before retention expires.

Use the sibling game's `docs/OBSERVATORY.md` for connector operation. Do not
copy its environment files or credentials into this repository.
