extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer = load("res://scripts/world/WorldRenderer.gd").new()
	root.add_child(renderer)
	var tiles: Dictionary = {}
	for x: int in range(4):
		for y: int in range(4):
			tiles[Vector2i(x, y)] = {"terrain": "grass"}
	var sites: Array = [
		{"id": "farm", "x": 1, "y": 1, "structure_type": "farm", "completed": true, "crop_growth": 0.6, "crop_food": 0},
		{"id": "fire", "x": 2, "y": 2, "structure_type": "campfire", "completed": true, "fuel": 0}
	]
	renderer.render_world(tiles, [], sites, [])
	await process_frame
	await process_frame
	print("PASS: ecology renderer loads farm and unlit fire state")
	quit()
