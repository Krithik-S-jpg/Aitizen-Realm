extends RefCounted
class_name RuntimeConfig

const CONFIG_PATH := "res://config/runtime.json"
const DEFAULT_HTTP_BASE := "http://127.0.0.1:8000"

static var _cached: Dictionary = {}


static func http_url(path: String) -> String:
	return str(_config().get("http_base_url", DEFAULT_HTTP_BASE)).trim_suffix("/") + path


static func websocket_url(path: String) -> String:
	var base := str(_config().get("websocket_base_url", ""))
	if base.is_empty():
		base = str(_config().get("http_base_url", DEFAULT_HTTP_BASE)).replace("http://", "ws://").replace("https://", "wss://")
	return base.trim_suffix("/") + path


static func _config() -> Dictionary:
	if not _cached.is_empty():
		return _cached
	var file := FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if file == null:
		return {"http_base_url": DEFAULT_HTTP_BASE}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	_cached = parsed if parsed is Dictionary else {"http_base_url": DEFAULT_HTTP_BASE}
	return _cached
