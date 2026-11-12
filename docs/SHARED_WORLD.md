# Shared player world

1. Sign in as owner and create or load your intended world in the game.
2. Open `/admin/world` on the same backend host. The administrator link on the player sign-in page also takes an already signed-in owner there.
3. Name the current world and choose **Set this world and open player joins**.
4. Players sign in at `/account` using email or Google. A verified sign-in creates one autonomous Utility AI citizen named from that account's display name. Accounts signed in before opening can use **Join the shared world**.
5. Repeated sign-ins reuse the account's citizen. Inactive/deceased citizens are not automatically replaced. Closing new joins leaves existing citizens intact.
6. Pause and save a checkpoint after designation and after new citizens join. Load that checkpoint after a backend restart. Settings and account links travel in the world payload. This feature does not add automatic cloud recovery; unsaved joins can be lost on a free-host restart.

New worlds and older saves default to closed joins. Changing the loaded world changes the shared world: this deployment runs one world, not separate player worlds. Run exactly one backend worker for atomic account joins.

Player sessions open a responsive dashboard at `/account`: a nearby overhead terrain map follows their citizen and refreshes every five seconds, with needs bars, important memories and activity. **Enter shared world** opens `/game/` in a read-only player view. It follows the account's citizen, shows live needs and provides observation layers and a return link for profile/chat. Players can pan the camera and resume following their citizen.

Player game data polls every two seconds; terrain refreshes every thirty seconds. It reads existing terrain only and never generates chunks or a default world. Lost sessions and unavailable worlds show a waiting/reconnecting indicator; use the account link to sign in again. It cannot recover an unsaved world after a server restart.

The server derives citizen ownership from the signed session, filters citizen data, and rejects player access to all owner APIs and WebSockets. Hiding admin controls is only a presentation measure. Chat is scoped to the signed-in account and uses the existing dialogue service; replies clearly identify simulation-status fallback when Ollama is unavailable. Chat does not execute commands. Citizens use existing Utility AI; hosted local-Ollama connectivity is separate work.
