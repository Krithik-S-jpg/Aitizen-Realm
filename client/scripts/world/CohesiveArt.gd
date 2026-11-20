extends RefCounted
## Shared textures and measured regions, reused by the world and crafting UI.
static var _regions: Dictionary = {}
static var _textures: Dictionary = {}
static var _icons: Dictionary = {}

static func regions(group: String) -> Dictionary:
	if _regions.is_empty():
		_regions = JSON.parse_string(FileAccess.get_file_as_string("res://config/cohesive_art.json"))
	return _regions.get(group,{})

static func texture(group: String) -> Texture2D:
	if not _textures.has(group):
		_textures[group] = load("res://assets/world/cohesive/"+group+".png")
	return _textures[group]

static func region(group: String, key: String) -> Rect2:
	var values: Array = regions(group).get(key,[])
	return Rect2(values[0],values[1],values[2],values[3]) if values.size() == 4 else Rect2()

static func icon(key: String) -> Texture2D:
	var aliases := {"stone_axe":"axe","wood_axe":"axe","stone_pickaxe":"pickaxe","iron_pickaxe":"pickaxe","rope":"fiber","food":"fruit","shelter":"shelter"}
	key = aliases.get(key,key)
	if _icons.has(key):
		return _icons[key]
	for group: String in ["structures","items","resources"]:
		var bounds := region(group,key)
		if bounds.has_area():
			var result := AtlasTexture.new()
			result.atlas = texture(group)
			result.region = bounds
			result.filter_clip = true
			_icons[key] = result
			return result
	return null
