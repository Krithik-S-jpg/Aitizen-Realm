# Large world save timeout mitigation

New saves losslessly compress the checkpoint payload with gzip/base64 before
sending it to Supabase. This reduces JSON parsing, JSONB storage and the payload
conversion performed by complete-save RPCs. Research archives remain normalized
in their existing tables; nothing is omitted from the world snapshot.

The storage envelope retains `world`, `calendar`, and `tick_rate` to satisfy
the original database CHECK constraint. The envelope's `world` is an empty
placeholder: the full world is in `data`, decoded by the backend on reads.
Calendar and tick rate are also available as small readable envelope fields.
Do not treat the raw placeholder as a playable world or restore it directly.

No database migration is required. Restart the backend to enable the codec.
The updated backend reads both old plain-JSON saves and new compressed saves.
Older backend versions cannot restore the new encoding. Payload decoding is
bounded to 256 MiB and rejects damaged/truncated data before restoration.

Refresh the save list before retrying an unconfirmed request. Do not automatically
retry writes, since a transport timeout can occur after a commit. This change
reduces payload-related load; it does not establish whether a hosted timeout was
also caused by database contention or archive volume. A real hosted save must be
confirmed separately. Local tests cover round-trip preservation, compatibility,
invalid data and all three storage write paths.
