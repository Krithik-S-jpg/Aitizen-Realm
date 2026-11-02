extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1000, 700)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(500, 100)
	root.add_child(renderer)
	var tiles := {}
	for x in range(12):
		for y in range(12):
			tiles[Vector2i(x, y)] = {"terrain": "mountain", "metadata": {"elevation": 0.85}}
	var floor_cells := []
	for x in range(-7, 8):
		for y in range(-6, 5):
			if Vector2(x / 1.5, y).length() < 4 or Vector2(x + 4, y + 3).length() < 3.5 or Vector2(x - 4, y + 3).length() < 3.5:
				floor_cells.append([x, y])
	tiles[Vector2i(5, 5)] = {"terrain": "stone", "metadata": {"cave": {"id": "test", "floor": floor_cells}}}
	renderer.render_world(tiles, [], [], [{"id": "bat", "kind": "animal", "x": 5, "y": 5, "metadata": {"cave_animal": true, "cave_position": [1, 1], "species": "bat"}}])
	await create_timer(0.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/mountains.png")
	renderer.set_cave_view(true)
	assert(renderer._dynamic_layer.cave_view)
	assert(not renderer._terrain_mesh.visible)
	await create_timer(0.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/caves.png")
	renderer.set_underwater_view(true)
	assert(not renderer.cave_view)
	assert(not renderer._dynamic_layer.cave_view)
	print("PASS cave and mountain assets, layer isolation")
	quit()
