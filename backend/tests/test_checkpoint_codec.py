import json
import pytest
import asyncio
import httpx
from app.infrastructure.repositories.supabase_checkpoints import SupabaseCheckpoints
from app.infrastructure.repositories.checkpoint_codec import encode_record, decode_record


def test_large_world_roundtrip_is_lossless_and_smaller():
    record = {"id": "slot", "payload": {"world": {"tiles": [
        {"x": x, "terrain": "grass", "metadata": {"elevation": .5}}
        for x in range(10000)]}, "calendar": {"day": 3}, "tick_rate": 4}}
    encoded = encode_record(record)
    assert {"world", "calendar", "tick_rate"} <= encoded["payload"].keys()
    assert len(json.dumps(encoded)) < len(json.dumps(record)) / 5
    assert decode_record(encoded) == record
    assert "encoding" not in record["payload"]


def test_legacy_and_metadata_records_are_unchanged():
    for record in [{"id": "slot"}, {"payload": {"world": {}, "tick_rate": 1}}]:
        assert decode_record(record) == record


def test_bad_compressed_data_is_rejected():
    for payload in [{"encoding": "future"}, {"encoding": "gzip-json-v1", "data": "garbage"}]:
        with pytest.raises(ValueError):
            decode_record({"payload": payload})


def test_all_save_modes_encode_and_reads_decode(monkeypatch):
    record = {"id": "slot", "payload": {"world": {"citizens": ["one"]}}}
    sent = []
    def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json=[encode_record(record)])
        body = json.loads(request.content)
        stored = body.get("p_checkpoint", body)
        assert decode_record(stored) == record
        sent.append(request.url.path)
        return httpx.Response(200, json=[{"id": "slot"}] if request.url.path.endswith("simulation_checkpoints") else {"id": "slot"})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    async def exercise():
        store = SupabaseCheckpoints("https://example.test", "sb_secret_test")
        await store.save(record)
        await store.save_complete(record, {})
        await store.overwrite(record, {})
        assert await store.read() == [record]
    asyncio.run(exercise())
    assert len(sent) == 3
