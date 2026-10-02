"""Atomic Supabase persistence for explicit research archives."""

import httpx


class SupabaseResearchArchive:
    """Calls one transactional database function through the Supabase Data API."""

    def __init__(self, url: str, key: str) -> None:
        """Require encrypted transport and a server-side key."""
        if not url.startswith("https://") or not key:
            raise ValueError("Configure HTTPS SUPABASE_URL and SUPABASE_SECRET_KEY")
        self._url = url.rstrip("/") + "/rest/v1/rpc/archive_simulation"
        self._headers = {"apikey": key, "Content-Type": "application/json"}
        if not key.startswith("sb_secret_"):
            self._headers["Authorization"] = f"Bearer {key}"

    async def save(self, archive: dict) -> str:
        """Persist a complete normalized archive in one database transaction."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._url, headers=self._headers, json={"p_archive": archive}
            )
            response.raise_for_status()
            return str(response.json())
