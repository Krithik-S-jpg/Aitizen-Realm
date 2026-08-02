# WorldLoader.gd
extends Node
class_name WorldLoader

## Validates and parses raw backend JSON payloads into robust, type-safe Godot models.

func parse_world_data(data: Dictionary) -> Dictionary:
	var parsed_world = {
		"width": 0,
		"height": 0,
		"chunk_size": 16,
		"tiles": {} # Vector2i -> Dictionary
	}

	if not data.has("width") or not data.has("height") or not data.has("tiles"):
		return {}

	parsed_world["width"] = int(data["width"])
	parsed_world["height"] = int(data["height"])
	parsed_world["chunk_size"] = int(data.get("chunk_size", 16))

	var tiles_list = data["tiles"]
	if typeof(tiles_list) != TYPE_ARRAY:
		return {}

	for tile_data in tiles_list:
		if typeof(tile_data) != TYPE_DICTIONARY:
			continue
		if not tile_data.has("x") or not tile_data.has("y") or not tile_data.has("terrain"):
			continue

		var x = int(tile_data["x"])
		var y = int(tile_data["y"])
		var terrain = str(tile_data["terrain"]).to_lower()
		var id = str(tile_data.get("id", ""))
		var metadata = tile_data.get("metadata", {})

		parsed_world["tiles"][Vector2i(x, y)] = {
			"x": x,
			"y": y,
			"terrain": terrain,
			"id": id,
			"metadata": metadata
		}

	return parsed_world
