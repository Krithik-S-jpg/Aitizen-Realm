"""Lossless storage envelope; legacy plain JSON checkpoints remain readable."""

import base64
import gzip
import json
import zlib

MAX_DECODED_BYTES = 256 * 1024 * 1024


def encode_record(record: dict) -> dict:
    raw = json.dumps(record["payload"], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_DECODED_BYTES:
        raise ValueError("World save exceeds the supported uncompressed size (256 MiB).")
    return {**record, "payload": {
        # Keep the required SQL envelope keys. The complete payload is encoded
        # below; these small fields also permit database-side inspection.
        "world": {},
        "calendar": record["payload"].get("calendar", {}),
        "tick_rate": record["payload"].get("tick_rate", 1),
        "encoding": "gzip-json-v1",
        "data": base64.b64encode(gzip.compress(raw, compresslevel=6, mtime=0)).decode("ascii"),
    }}


def decode_record(record: dict) -> dict:
    payload = record.get("payload")
    if not isinstance(payload, dict) or "encoding" not in payload:
        return record
    if payload.get("encoding") != "gzip-json-v1":
        raise ValueError("Unsupported world save encoding.")
    try:
        compressed = base64.b64decode(payload["data"], validate=True)
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        raw = decoder.decompress(compressed, MAX_DECODED_BYTES + 1)
        if len(raw) > MAX_DECODED_BYTES or not decoder.eof or decoder.unused_data:
            raise ValueError("Invalid or oversized compressed world save.")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("World save payload must be an object.")
        return {**record, "payload": decoded}
    except (KeyError, TypeError, ValueError, zlib.error) as error:
        raise ValueError("World save is corrupt or exceeds the supported size.") from error
