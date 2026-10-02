extends RefCounted

# Shared atlas cache: no image decoding or region scanning in the frame loop.
static var _catalog: Dictionary = {}
static var _textures: Dictionary = {}

static func profile(avatar: String) -> Dictionary:
	if _catalog.is_empty():
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://config/citizen_actions.json"))
		if parsed is Dictionary:
			_catalog = parsed
	return _catalog.get(avatar, _catalog.get("scout", {}))

static func texture(avatar: String, action := "idle") -> Texture2D:
	var data := profile(avatar)
	var key := "gather_texture" if action in ["gather", "pluck", "eat"] and data.has("gather_texture") else "texture"
	var path: String = data.get(key, "")
	if not _textures.has(path):
		_textures[path] = load(path)
	return _textures[path] as Texture2D

static func scale_for(avatar: String, action: String) -> float:
	var data := profile(avatar)
	return float(data.get("gather_scale", data.get("scale", 0.45))) if action in ["gather", "pluck", "eat"] else float(data.get("scale", 0.45))

static func action_frames(avatar: String, action: String) -> Array:
	var aliases := {"walk": "move", "run": "move", "rest": "sleep", "pluck": "gather", "eat": "gather", "craft": "build"}
	var key: String = aliases.get(action, action)
	var actions: Dictionary = profile(avatar).get("actions", {})
	return actions.get(key, actions.get("idle", []))

static func portrait(avatar: String) -> AtlasTexture:
	var frame: Array = action_frames(avatar, "idle")[0]
	var result := AtlasTexture.new()
	result.atlas = texture(avatar)
	result.region = Rect2(frame[0], frame[1], frame[2], frame[3])
	return result
