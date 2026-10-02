extends SceneTree


func _initialize() -> void:
	var minimap := WorldMinimap.new()
	minimap.size = Vector2(214, 132)
	root.add_child(minimap)
	var tiles: Dictionary = {}
	for x: int in range(64):
		for y: int in range(64):
			tiles[Vector2i(x, y)] = {"terrain": "water" if x < 8 else "grass"}
	var world := {
		"width": 64,
		"height": 64,
		"tiles": tiles,
		"entities": [],
		"structures": []
	}
	minimap.update_world(world)
	assert(minimap.get_terrain_cache_build_count() == 1)
	for index: int in range(30):
		minimap.update_camera(Vector2i(index, index))
		minimap.update_entities([{"x": index, "y": index}])
	assert(minimap.get_terrain_cache_build_count() == 1)
	minimap.update_world(world)
	assert(minimap.get_terrain_cache_build_count() == 2)
	print("PASS: minimap terrain remains cached during camera and entity updates")
	quit()
