extends RefCounted

# Shared atlas cache: no image decoding or region scanning in the frame loop.
static var _catalog: Dictionary = {}
static var _textures: Dictionary = {}

static func profile(avatar: String) -> Dictionary:
	if _catalog.is_empty():
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://config/citizen_actions.json"))
		if parsed is Dictionary:
			_catalog = parsed
		# Complete identity overrides replace the old catalog entry, including any
		# old gather texture. Stable avatar IDs keep existing saves compatible.
		var human: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://config/citizen_human_actions.json"))
		if human is Dictionary:
			_catalog.merge(human, true)
		var care_path := "res://assets/pixel_art/citizens/aster_care_v1.png"
		var care_texture := load(care_path) as Texture2D
		var care_image := care_texture.get_image() if care_texture != null else null
		var scout: Dictionary = _catalog.get("scout", {})
		if care_image != null and not scout.is_empty():
			var care_actions := ["carry_infant", "cradle", "teach"]
			for row in range(3):
				var frames: Array = []
				for column in range(4):
					var cell := Rect2i(column * care_image.get_width() / 4, row * care_image.get_height() / 3, care_image.get_width() / 4, care_image.get_height() / 3)
					var bounds := care_image.get_region(cell).get_used_rect()
					frames.append([cell.position.x + bounds.position.x, cell.position.y + bounds.position.y, bounds.size.x, bounds.size.y, -bounds.size.x / 2.0])
				scout.actions[care_actions[row]] = frames
				if not scout.has("action_textures"):
					scout["action_textures"] = {}
				if not scout.has("action_scales"):
					scout["action_scales"] = {}
				scout.action_textures[care_actions[row]] = care_path
				scout.action_scales[care_actions[row]] = 48.0 / maxf(1, frames[0][3])
	if avatar.begins_with("family_") and not _catalog.has(avatar):
		var rows := {"family_infant": 0, "family_toddler_male": 1, "family_toddler_female": 2, "family_child_male": 3, "family_child_female": 4, "family_elder_male": 5}
		if rows.has(avatar):
			var path := "res://assets/pixel_art/family_stages_v1.png"
			var sheet := load(path) as Texture2D
			var pixels := sheet.get_image()
			var edges := [0, 238, 488, 718, 952, 1220, 1536]
			var row: int = rows[avatar]
			var frames: Array = []
			for column in range(4):
				var cell := Rect2i(column * 256, edges[row], 256, edges[row + 1] - edges[row])
				var bounds := pixels.get_region(cell).get_used_rect()
				frames.append([cell.position.x + bounds.position.x, cell.position.y + bounds.position.y, bounds.size.x, bounds.size.y, -bounds.size.x / 2.0])
			var height: float = [18.0, 25.0, 25.0, 34.0, 34.0, 46.0][row]
			_catalog[avatar] = {"texture": path, "scale": height / maxf(1, frames[0][3]), "actions": {"idle": [frames[0]], "move": frames, "play": frames, "rest": [frames[0]]}}
	if avatar in ["juniper", "rowan"] and not _catalog.has(avatar):
		var path := "res://assets/pixel_art/%s_actions_v1.png" % avatar
		if avatar == "rowan":
			path = "res://assets/pixel_art/rowan_actions_v2.png"
		var texture_asset := load(path) as Texture2D
		var source := texture_asset.get_image()
		var cell := Vector2i(source.get_width() / 4, source.get_height() / 8)
		var actions: Dictionary = {}
		var names := ["idle", "move", "sleep", "gather", "build", "swim", "cook", "hunt"]
		for row: int in range(8):
			var frames: Array = []
			for column: int in range(4):
				var origin := Vector2i(column * cell.x, row * cell.y)
				var bounds := source.get_region(Rect2i(origin, cell)).get_used_rect()
				frames.append([origin.x + bounds.position.x, origin.y + bounds.position.y, bounds.size.x, bounds.size.y, -bounds.size.x / 2.0])
			actions[names[row]] = frames
		actions["carry"] = actions["move"]
		actions["mine"] = actions["build"]
		actions["chop"] = actions["build"]
		_catalog[avatar] = {"texture": path, "scale": 68.0 / float(actions.idle[0][3]), "actions": actions}
	return _catalog.get(avatar, _catalog.get("scout", {}))

static func texture(avatar: String, action := "idle") -> Texture2D:
	var data := profile(avatar)
	var key := "gather_texture" if action in ["gather", "pluck", "eat"] and data.has("gather_texture") else "texture"
	var path: String = data.get(key, "")
	path = str(data.get("action_textures", {}).get(action, path))
	if not _textures.has(path):
		_textures[path] = load(path)
	return _textures[path] as Texture2D

static func has_native_action(avatar: String, action: String) -> bool:
	return profile(avatar).get("actions", {}).has(action)

static func scale_for(avatar: String, action: String) -> float:
	var data := profile(avatar)
	var ratio := float(data.get("gather_scale", data.get("scale", 0.45))) if action in ["gather", "pluck", "eat"] else float(data.get("scale", 0.45))
	ratio = float(data.get("action_scales", {}).get(action, ratio))
	if avatar.begins_with("family_"):
		return ratio
	var idle: Array = data.get("actions", {}).get("idle", [])
	if not idle.is_empty():
		var standing_height := float(idle[0][3]) * float(data.get("scale", 0.45))
		ratio *= 48.0 / maxf(1, standing_height)
	return ratio

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
