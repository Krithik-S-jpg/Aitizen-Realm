extends SceneTree


func _init() -> void:
	var loader_script := load("res://scripts/world/WorldLoader.gd")
	var loader: Node = loader_script.new()
	var resource := {
		"id": "tree-1", "type": "TREE", "x": -1, "y": 2,
		"quantity": 0.0, "capacity": 80.0, "visual_state": "fallen",
		"state_changed_tick": 42, "reserved_by": "agent-1",
		"reservation_expires_at": 45, "produce_type": null
	}
	loader.load_world_from_json({"width": 16, "height": 16, "tiles": [], "resources": [resource]})
	var initial: Dictionary = loader.stored_world_data["resources"][0]
	assert(initial["visual_state"] == "fallen")
	assert(initial["state_changed_tick"] == 42)
	assert(initial["reserved_by"] == "agent-1")
	assert(initial["produce_type"] == null)
	assert(initial["type"] == "tree")
	assert(resource["type"] == "TREE", "Parsing must not mutate the payload")
	resource["visual_state"] = "stump"
	resource["state_changed_tick"] = 72
	loader.merge_chunk_data({"chunk_x": -1, "chunk_y": 0, "tiles": [], "resources": [resource]})
	var chunk: Dictionary = loader.stored_world_data["resources"][0]
	var live: Dictionary = loader_script.parse_resource(resource)
	assert(chunk == live, "Chunk and live normalization must agree")
	assert(chunk["visual_state"] == "stump")
	assert(loader.stored_world_data["resources"].size() == 1)
	assert(loader_script.parse_resource({})["visual_state"] == "standing")
	loader.free()
	print("PASS: resource snapshots, chunks and live updates preserve lifecycle and reservation state")
	quit()
