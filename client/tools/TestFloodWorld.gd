extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(570, 130)
	root.add_child(renderer)
	var tiles := {}
	for x in range(10):
		for y in range(10):
			tiles[Vector2i(x, y)] = {"terrain": "water" if x == 5 else "grass", "metadata": {}}
	var structures := [{"id": "bridge", "x": 5, "y": 4, "structure_type": "bridge", "completed": true, "progress_ratio": 1.0}]
	var citizens := [{"id": "evacuee", "kind": "agent", "name": "Seeking dry ground", "x": 4, "y": 6, "avatar_id": "rowan", "action": "move", "metadata": {}}]
	renderer.render_world(tiles, [], structures, citizens)
	renderer.configure_environment({"weather": "RAIN", "weather_intensity": .8, "wind_speed": 10})
	var flood := []
	for y in range(10):
		if y != 4:
			flood.append({"x": 4, "y": y})
	renderer.update_floods(flood)
	assert(renderer._tiles[Vector2i(4, 6)].metadata.flooded)
	await create_timer(.6).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/flood-active.png")
	citizens[0].x = 3
	renderer.update_entities(citizens)
	renderer.update_floods([])
	assert(not renderer._tiles[Vector2i(4, 6)].metadata.has("flooded"))
	await create_timer(.6).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/flood-receded.png")
	print("PASS: flooded bank, recession, bridge and citizen rendering")
	quit()
