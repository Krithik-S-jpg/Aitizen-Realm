"""Configuration rejects public keys without exposing their content."""

import base64
import json

import pytest

from app.infrastructure.repositories.supabase_checkpoints import SupabaseCheckpoints


@pytest.mark.parametrize("key", [
    "sb_publishable_example",
    "header." + base64.urlsafe_b64encode(json.dumps({"role": "anon"}).encode()).decode().rstrip("=") + ".signature",
])
def test_public_credentials_rejected(key: str) -> None:
    with pytest.raises(ValueError, match="public/anon") as error:
        SupabaseCheckpoints("https://example.supabase.co", key)
    assert key not in str(error.value)


def test_server_secret_accepted() -> None:
    SupabaseCheckpoints("https://example.supabase.co", "sb_secret_example")
