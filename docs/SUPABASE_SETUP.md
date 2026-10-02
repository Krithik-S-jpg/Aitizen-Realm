# Supabase checkpoints

Implemented: authenticated manual checkpoints, paused restore, and transactional research archives for simulation runs, experiments, metrics and world events. Active simulation remains in memory. Scheduled backups and automatic startup recovery are not implemented.

### Where each kind of data lives

### Complete saves (October 2026)

**Overwrite slots:** also apply `supabase/migrations/202610020002_overwrite_save.sql`. In Settings, refresh saves, select the exact slot and choose **Overwrite selected save…**. Confirm after pausing. Its ID, name and creation date are preserved; its snapshot is replaced. Complete-save mode links a new archive transactionally; old research archives remain historical. Snapshot-only overwrite clears the old archive link rather than presenting it as current. Missing slots are rejected, never recreated. Concurrent confirmed overwrites are serialized by a row lock; the last successful write wins. **Save as new** always creates a separate slot. Hosted overwrite has not been verified and no existing hosted save was overwritten during development.

Apply `supabase/migrations/202610020001_complete_save.sql` in the Supabase SQL editor after the two earlier migrations. It adds a checkpoint-to-research-run relationship and a server-only transactional save function. Existing saves are preserved.

Settings now defaults to **Include research, metrics and event history (complete save)**. Pause and Save world to store the snapshot plus retained research history atomically. Disable the checkbox for the older snapshot-only path. The response reports real archived row counts; zero experiments is valid when none have been created. A transport timeout is an unknown outcome: refresh saves before retrying.

Hosted verification on October 2: checkpoint read succeeded (three saved rows); research tables were readable. The new checkpoint column query was rejected, so the migration and hosted complete-save write are not yet verified. No hosted writes were performed.

This is explicit persistence, not continuous sync or automatic startup recovery. Loading restores playable world state; archived research remains separate historical data, not a replay engine.

- **Save world** writes one row to simulation_checkpoints. Its payload.world JSON includes entities (citizens and animals), inventories, resources, structures, terrain chunks, goals/actions, movement plans, personal memory episodes, knowledge, messages, relationships, groups, households and settlement jobs. These are not separate database tables.
- The checkpoint also includes calendar controls and tick rate; it is a restorable world snapshot, not an unlimited historical replay.
- **POST /api/v1/research/archive**, with the simulation paused and the admin token, writes simulation_runs, research_experiments, metrics_snapshots and world_events through the transactional archive function. Saving a checkpoint does not call this endpoint. Only retained research/history data is archived.
- The schema visualizer displays table definitions and relationships, not whether data is present. Use the table editor to inspect rows. Neither path currently provides continuous database synchronization.

1. Apply `supabase/migrations/202609240001_checkpoints.sql` to your Supabase project using its SQL editor or migration workflow.
   Then apply `supabase/migrations/202609250001_research_archive.sql`. After refreshing the schema visualizer you should see five tables in total.
2. Configure the following in the backend environment (or local ignored `backend/.env`):

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SECRET_KEY=YOUR_SERVER_SECRET_KEY
CHECKPOINT_ADMIN_TOKEN=YOUR_LONG_RANDOM_ADMIN_TOKEN
```

Never put Supabase keys in Godot, source control, screenshots or chat. Supabase secret/service-role keys bypass RLS and must stay server-side: https://supabase.com/docs/guides/database/secure-data

In Godot, open Settings -> World saves / Supabase. Enter only the separate CHECKPOINT_ADMIN_TOKEN in the masked session-only field. Click Check connection to verify checkpoint-table read access. Pause world, enter a save name and select Save world. Refresh saves, select a checkpoint and confirm Load selected world to restore it paused. The token is not written to client configuration. Use HTTPS when connecting to a non-local backend. The connection check does not prove write permissions; successful saving does.

3. Restart the backend. Pause the simulation before saving.
4. In the API docs, send `X-Admin-Token` with the configured admin token:
   - `POST /api/v1/checkpoints` with `{"label":"Before winter"}`.
   - `GET /api/v1/checkpoints` lists the latest 50 backups.
   - `GET /api/v1/checkpoints/{id}` downloads one complete backup.
   - `POST /api/v1/checkpoints/{id}/restore` restores the saved world, tick and calendar paused. Stop or pause first; pending scheduler jobs must be cleared. Reload the Godot world before resuming. Previous in-memory analytics history is cleared because v1 checkpoints do not include it.
   - `POST /api/v1/research/archive` stores the paused run's experiments, metrics and world events atomically.

The version-1 payload includes actual World data, calendar configuration, tick rate and the recorded tick. No database request occurs on ordinary simulation ticks. No public database access policy is installed. The API returns sanitized storage errors, not credentials or database error bodies.

The research archive is immutable history; it does not replace the active in-memory world. It uses one PostgreSQL function so a failed archive cannot leave half of its tables saved. Hosted migration/connectivity must be verified on your project; mocked API tests are not proof of a live Supabase connection. Checkpoints do not currently include scheduler jobs and must not be described as full replay checkpoints.
