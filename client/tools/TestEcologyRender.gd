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
	var resources: Array = [
		{"id": "remains", "type": "carcass", "x": 3, "y": 1, "quantity": 7.0, "capacity": 12.0, "visual_state": "decaying"}
	]
	var animals: Array = [
		{"id": "migrant", "kind": "animal", "x": 1, "y": 2, "action": "migrate", "metadata": {"species": "deer", "age_stage": "adult", "age_days": 40}}
	]
	renderer.render_world(tiles, resources, sites, animals)
	await process_frame
	await process_frame
	var terrain_mesh = renderer._terrain_mesh.mesh
	assert(terrain_mesh != null, "Terrain must have a batched surface")
	renderer.update_resources(resources)
	renderer.update_structures(sites)
	await process_frame
	assert(renderer._terrain_mesh.mesh == terrain_mesh, "Dynamic resource and building updates must reuse static terrain")
	print("PASS: ecology renderer loads farm and unlit fire state")
	quit()
