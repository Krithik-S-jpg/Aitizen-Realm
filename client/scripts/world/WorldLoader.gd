# WorldLoader.gd
extends Node
class_name WorldLoader

## Validates raw JSON payloads and registers parsed tiles into accessible memory grids.

signal world_loaded(parsed_world: Dictionary)
signal chunk_loaded(chunk_position: Vector2i, parsed_world: Dictionary)
signal validation_failed(error_message: String)

var stored_world_data: Dictionary = {}

## Processes, validates, and stores loaded map boundaries and tile definitions.
func load_world_from_json(data: Dictionary) -> void:
	if not data.has("width") or not data.has("height") or not data.has("tiles"):
		validation_failed.emit("Missing mandatory schema keys (width, height, or tiles).")
		return

	var parsed_world = {
		"schema_version": str(data.get("schema_version", "legacy")),
		"layer_support": data.get("layer_support", {}),
		"width": int(data["width"]),
		"height": int(data["height"]),
		"chunk_size": int(data.get("chunk_size", 16)),
		"seed": int(data.get("seed", 0)),
		"resources": [],
		"structures": [],
		"entities": [],
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
			"metadata": metadata,
			"walkable": bool(tile_data.get("walkable", true)),
			"movement_cost": float(tile_data.get("movement_cost", 1.0))
		}

	var resources_list = data.get("resources", [])
	if typeof(resources_list) == TYPE_ARRAY:
		for resource_data in resources_list:
			if typeof(resource_data) != TYPE_DICTIONARY:
				continue
			if not resource_data.has("x") or not resource_data.has("y") or not resource_data.has("type"):
				continue
			parsed_world["resources"].append(parse_resource(resource_data))

	var structures_list = data.get("structures", [])
	if typeof(structures_list) == TYPE_ARRAY:
		for structure_data in structures_list:
			if typeof(structure_data) == TYPE_DICTIONARY:
				parsed_world["structures"].append(structure_data.duplicate(true))

	var entities_list: Variant = data.get("entities", [])
	if typeof(entities_list) == TYPE_ARRAY:
		for entity_data: Variant in entities_list:
			if typeof(entity_data) == TYPE_DICTIONARY:
				parsed_world["entities"].append((entity_data as Dictionary).duplicate(true))

	stored_world_data = parsed_world
	world_loaded.emit(parsed_world)


func merge_chunk_data(data: Dictionary) -> void:
	if stored_world_data.is_empty() or not data.has("tiles"):
		validation_failed.emit("Cannot merge chunk before the initial world is loaded.")
		return

	for tile_data in data["tiles"]:
		if typeof(tile_data) != TYPE_DICTIONARY:
			continue
		var x: int = int(tile_data["x"])
		var y: int = int(tile_data["y"])
		stored_world_data["tiles"][Vector2i(x, y)] = {
			"x": x,
			"y": y,
			"terrain": str(tile_data["terrain"]).to_lower(),
			"id": str(tile_data.get("id", "")),
			"metadata": tile_data.get("metadata", {}),
			"walkable": bool(tile_data.get("walkable", true)),
			"movement_cost": float(tile_data.get("movement_cost", 1.0))
		}

	var resources_by_id: Dictionary = {}
	for existing: Dictionary in stored_world_data["resources"]:
		resources_by_id[str(existing["id"])] = existing
	for resource_data in data.get("resources", []):
		if typeof(resource_data) != TYPE_DICTIONARY:
			continue
		resources_by_id[str(resource_data["id"])] = parse_resource(resource_data)
	stored_world_data["resources"] = resources_by_id.values()

	var structures_by_id: Dictionary = {}
	for existing: Dictionary in stored_world_data["structures"]:
		structures_by_id[str(existing.get("id", ""))] = existing
	for structure_data in data.get("structures", []):
		if typeof(structure_data) == TYPE_DICTIONARY:
			structures_by_id[str(structure_data.get("id", ""))] = structure_data.duplicate(true)
	stored_world_data["structures"] = structures_by_id.values()

	var entities_by_id: Dictionary = {}
	for existing: Dictionary in stored_world_data["entities"]:
		entities_by_id[str(existing.get("id", ""))] = existing
	for entity_data: Variant in data.get("entities", []):
		if typeof(entity_data) == TYPE_DICTIONARY:
			var entity: Dictionary = entity_data as Dictionary
			entities_by_id[str(entity.get("id", ""))] = entity.duplicate(true)
	stored_world_data["entities"] = entities_by_id.values()

	var chunk_position := Vector2i(int(data["chunk_x"]), int(data["chunk_y"]))
	chunk_loaded.emit(chunk_position, stored_world_data)


static func parse_resource(data: Dictionary) -> Dictionary:
	# Preserve backend fields across snapshots, chunks, and live updates.
	var resource := data.duplicate(true)
	resource["id"] = str(data.get("id", ""))
	resource["type"] = str(data.get("type", "")).to_lower()
	for key: String in ["x", "y", "variant", "state_changed_tick"]:
		resource[key] = int(data.get(key, 0))
	for key: String in ["quantity", "capacity", "produce_quantity", "produce_capacity"]:
		resource[key] = float(data.get(key, 0.0))
	resource["growth"] = float(data.get("growth", 1.0))
	resource["visual_state"] = str(data.get("visual_state", "standing"))
	return resource
