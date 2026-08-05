# WorldLoader.gd
extends Node
class_name WorldLoader

## Validates raw JSON payloads and registers parsed tiles into accessible memory grids.

signal world_loaded(parsed_world: Dictionary)
signal validation_failed(error_message: String)

var stored_world_data: Dictionary = {}

## Processes, validates, and stores loaded map boundaries and tile definitions.
func load_world_from_json(data: Dictionary) -> void:
	if not data.has("width") or not data.has("height") or not data.has("tiles"):
		validation_failed.emit("Missing mandatory schema keys (width, height, or tiles).")
		return

	var parsed_world = {
		"width": int(data["width"]),
		"height": int(data["height"]),
		"chunk_size": int(data.get("chunk_size", 16)),
		"tiles": {} # Vector2i -> Dictionary
	}

	var tiles_list = data["tiles"]
	if typeof(tiles_list) != TYPE_ARRAY:
		validation_failed.emit("'tiles' key is not a valid JSON Array.")
		return

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

	stored_world_data = parsed_world
	world_loaded.emit(parsed_world)
