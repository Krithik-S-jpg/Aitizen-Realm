extends SceneTree

## Deterministic visual fixture; never connects to or mutates a live simulation.
func _initialize() -> void:
	call_deferred("_preview")

func _preview() -> void:
	root.size = Vector2i(1152, 648)
	var renderer = load("res://scripts/world/WorldRenderer.gd").new()
	root.add_child(renderer)
	renderer.position = Vector2(576, -190)
	var tiles: Dictionary = {}
	var resources: Array = []
	for x: int in range(30):
		for y: int in range(30):
			var terrain := "grass"
			if x > 16:
				terrain = "snow"
			elif y > 18:
				terrain = "water"
			tiles[Vector2i(x, y)] = {"terrain": terrain, "metadata": {"variant": (x + y) % 4}}
			if terrain == "grass" and (x * 7 + y * 11) % 13 == 0:
				resources.append({"id": "%s,%s" % [x,y], "type": "tree", "x": x, "y": y, "growth": 0.85, "variant": x % 2, "produce_quantity": 0, "capacity": 80})
	renderer.render_world(tiles, resources)
	var template = load("res://scenes/Main.tscn").instantiate()
	var hud = template.get_node("UI/DebugPanel")
	hud.get_parent().remove_child(hud)
	template.free()
	root.add_child(hud)
	hud.update_status(true)
	hud.update_world_info("preview fixture", 30, 30, 16, 42, 900, resources.size())
	await create_timer(0.8).timeout
	assert(root.get_visible_rect().encloses(hud._command_bar.get_global_rect()))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/observatory-preview.png")
	hud._set_intel_visible(true)
	await create_timer(0.3).timeout
	assert(hud._world_summary.size.y >= 64)
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/observatory-overview.png")
	print("PASS: observatory visual fixture captured")
	quit()
