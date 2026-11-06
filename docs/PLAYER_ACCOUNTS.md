# Player accounts setup

Public visitors at `/` or `/login` land on `/account`. Owner access is available
through the discreet administrator link at `/admin/login`; its form continues
posting to `/login`. The shared responsive design uses CSS scenery and motion,
honors reduced-motion preferences, and needs no external scripts or image fetches.

The hosted owner login remains administrator-only. `/account` adds player
email/password registration, verified-email login, and Google OAuth with PKCE.
Player sessions never unlock the owner API or the admin Godot client.

Render environment:
- SUPABASE_URL: the existing Supabase project URL.
- SUPABASE_PUBLISHABLE_KEY: the project's publishable (or legacy anon) key.
  Never use the service-role/secret key for this setting.
- PUBLIC_BASE_URL: https://aitizen-realm-backend.onrender.com

In Supabase Authentication, enable Email with email confirmation, configure
Google's OAuth client ID and secret, set the Site URL to the hosted /account
page, and allow the exact redirect URL
https://aitizen-realm-backend.onrender.com/account/callback .
Follow https://supabase.com/docs/guides/auth/social-sign-in/auth-google for
Google's authorized callback URI and consent configuration. Provider credentials
and account verification must be entered by the owner in provider dashboards.

After confirming email, players sign in and click Join the shared world. The
admin must load a world first. One citizen is linked per Supabase user ID in
that world's entity metadata, including inactive citizens. Rejoining does not
replace a dead citizen. These links persist through world checkpoints, not
through unsaved Render restarts. Different/new worlds have separate links.

Current player portal shows their linked citizen and active status. Player
Godot spectator access, ownership-specific in-game controls, automatic joining
at registration, cloud recovery, and remote Ollama remain pending. Keep the
owner token private. Do not share it to let players access /game/.

Sessions last one hour; sign in again after expiry. No refresh token is stored.
Supabase rate limits email/auth operations. Verify live email delivery and
Google login after configuration; mocked unit tests do not verify providers.
