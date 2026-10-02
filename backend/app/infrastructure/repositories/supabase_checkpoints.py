"""Server-only Supabase checkpoint storage; never used on the tick hot path."""

import base64
import json
from uuid import UUID

import httpx


class SupabaseCheckpoints:
    """Stores immutable versioned snapshots through Supabase's Data API."""

    def __init__(self, url: str, key: str) -> None:
        """Require encrypted transport and server-side credentials."""
        if not url.startswith("https://") or not key:
            raise ValueError("Configure HTTPS SUPABASE_URL and SUPABASE_SECRET_KEY")
        # Decode only to reject known public credentials, never to authenticate.
        role = None
        if key.count(".") == 2:
            try:
                payload = key.split(".")[1]
                claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
                role = claims.get("role") if isinstance(claims, dict) else None
            except (ValueError, UnicodeError):
                pass
        if key.startswith("sb_publishable_") or role in {"anon", "authenticated"}:
            raise ValueError(
                "SUPABASE_SECRET_KEY contains a public/anon key. Configure a server secret "
                "or legacy service_role key in backend/.env, then restart the backend."
            )
        self._url = url.rstrip("/") + "/rest/v1/simulation_checkpoints"
        self._headers = {"apikey": key, "Prefer": "return=representation"}
        if not key.startswith("sb_secret_"):
            self._headers["Authorization"] = f"Bearer {key}"

    async def save(self, record: dict) -> dict:
        """Insert a checkpoint without overwriting previous history."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._url, headers=self._headers, json=record)
            response.raise_for_status()
            return response.json()[0]

    async def read(self, checkpoint_id: UUID | None = None) -> list[dict]:
        """List metadata, or retrieve one complete checkpoint by UUID."""
        params = {"order": "created_at.desc", "limit": "50"}
        if checkpoint_id is None:
            params["select"] = "id,label,tick,schema_version,created_at"
        else:
            params["id"] = f"eq.{checkpoint_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._url, headers=self._headers, params=params)
            response.raise_for_status()
            return response.json()

    async def save_complete(self, record: dict, archive: dict) -> dict:
        """One database transaction: checkpoint plus linked research archive."""
        url = self._url.rsplit("/", 1)[0] + "/rpc/save_complete_world"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self._headers,
                                         json={"p_checkpoint": record, "p_archive": archive})
            response.raise_for_status()
            return response.json()

    async def overwrite(self, record: dict, archive: dict | None) -> dict:
        """Update an existing slot only, with optional archive in one transaction."""
        url = self._url.rsplit("/", 1)[0] + "/rpc/overwrite_world_save"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self._headers,
                                         json={"p_checkpoint": record, "p_archive": archive})
            if response.status_code >= 400:
                try:
                    missing = response.json().get("code") == "P0002"
                except (ValueError, AttributeError):
                    missing = False
                if missing:
                    raise LookupError("Save not found")
            response.raise_for_status()
            return response.json()
