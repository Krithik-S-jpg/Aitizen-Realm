extends RefCounted
class_name RuntimeConfig

const CONFIG_PATH := "res://config/runtime.json"
const DEFAULT_HTTP_BASE := "http://127.0.0.1:8000"

static var _cached: Dictionary = {}

static func is_player() -> bool:
	return OS.has_feature("web") and bool(JavaScriptBridge.eval("window.AITIZEN_PLAYER === true", true))


static func http_url(path: String) -> String:
	if is_player():
		var routes := {"/api/v1/world": "world", "/api/v1/entities": "entities", "/api/v1/simulation": "state"}
		if routes.has(path):
			path = "/account/game-data/" + str(routes[path])
	return str(_config().get("http_base_url", DEFAULT_HTTP_BASE)).trim_suffix("/") + path


static func websocket_url(path: String) -> String:
	var base := str(_config().get("websocket_base_url", ""))
	if base.is_empty():
		base = str(_config().get("http_base_url", DEFAULT_HTTP_BASE)).replace("http://", "ws://").replace("https://", "wss://")
	return base.trim_suffix("/") + path


static func _config() -> Dictionary:
	if not _cached.is_empty():
		return _cached
	if OS.has_feature("web"):
		# Hosting supplies a public API origin, never a credential. Without an
		# override use the site's origin for a same-origin reverse proxy.
		var base: String = str(JavaScriptBridge.eval("window.AITIZEN_API_ORIGIN || window.location.origin", true)).trim_suffix("/")
		if not base.begins_with("https://") and not base.begins_with("http://localhost:") and not base.begins_with("http://127.0.0.1:"):
			base = str(JavaScriptBridge.eval("window.location.origin", true))
		_cached = {"http_base_url": base, "websocket_base_url": base.replace("https://", "wss://").replace("http://", "ws://")}
		return _cached
	var file := FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if file == null:
		return {"http_base_url": DEFAULT_HTTP_BASE}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	_cached = parsed if parsed is Dictionary else {"http_base_url": DEFAULT_HTTP_BASE}
	return _cached
