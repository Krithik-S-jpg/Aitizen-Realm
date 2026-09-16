extends SceneTree

## Isolated rendering fixture: no network or changes to the user's world.
func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1000, 640)
	var renderer = load("res://scripts/world/WorldRenderer.gd").new()
	root.add_child(renderer)
	renderer.position = Vector2(500, 160)
	var tiles: Dictionary = {}
	for x: int in range(12):
		for y: int in range(12):
			tiles[Vector2i(x, y)] = {"terrain": "grass"}
	var resources: Array = [
		{"id": "tree", "type": "tree", "x": 3, "y": 3, "growth": 1.0, "quantity": 80, "capacity": 80},
		{"id": "stone", "type": "stone", "x": 7, "y": 3, "quantity": 30, "capacity": 100}
	]
	var sites: Array = []
	for stage: int in range(4):
		sites.append({"x": 2 + stage * 2, "y": 8, "structure_type": "shelter", "completed": false, "progress_ratio": 0.1 + stage * 0.25})
	var miner := {"id": "miner", "kind": "agent", "x": 6, "y": 3, "action": "gather", "action_progress": 0.5, "action_target": {"resource_id": "stone", "resource_type": "stone", "resource_x": 7, "resource_y": 3, "x": 6, "y": 3}}
	renderer.render_world(tiles, resources, sites, [miner])
	assert(renderer._active_mining.has("stone"))
	miner["x"] = 1
	renderer.update_entities([miner])
	assert(renderer._active_mining.is_empty())
	miner["x"] = 6
	renderer.update_entities([miner])
	await create_timer(0.6).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/action-stages.png")
	resources[0]["visual_state"] = "fallen"
	renderer.update_resources(resources)
	await create_timer(0.4).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/tree-fall.png")
	print("PASS: mining proximity guard and action-stage rendering")
	quit()
