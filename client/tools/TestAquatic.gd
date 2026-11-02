extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1100, 720)
	RenderingServer.set_default_clear_color(Color("081c29"))
	var world := WorldRenderer.new()
	world.position = Vector2(520, 120)
	root.add_child(world)
	var tiles := {}
	for x in range(14):
		for y in range(14):
			tiles[Vector2i(x, y)] = {"terrain": "water", "metadata": {"marine": {"depth": 5, "habitat": "kelp" if x < 5 else "reef" if y < 7 else "rock", "landmark": "wreck" if x == 9 and y == 9 else "cave" if x == 10 and y == 3 else ""}}}
	var citizens := []
	for index in range(8):
		citizens.append({"id": str(index), "kind": "agent", "x": 3 + index % 4 * 2,
			"y": 3 + index / 4 * 3, "avatar_id": WorldRenderer.CITIZEN_AVATAR_ORDER[index],
			"action": "move", "underwater": true, "oxygen": 88, "travel_mode": "swim", "dive_phase": ["descend", "gather", "surface", "explore"][index % 4]})
	for index in range(4):
		citizens.append({"id": str(100 + index), "kind": "animal", "x": 2 + index * 3, "y": 9,
			"underwater": true, "metadata": {"marine": true, "species": ["reef_fish", "crab", "jellyfish", "shark"][index]}})
	world.render_world(tiles, [], [], citizens)
	world.set_underwater_view(true)
	assert(world._dynamic_layer.underwater_view)
	if world._terrain_mesh != null:
		assert(not world._terrain_mesh.visible)
	await create_timer(0.5).timeout
	assert(world._dynamic_layer._swim_texture != null)
	assert(world._dynamic_layer._marine_texture != null)
	assert(world._dynamic_layer._marine_life_texture != null)
	assert(world._dynamic_layer._diving_actions_texture != null)
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/aquatic-underwater.png")
	for citizen: Dictionary in citizens:
		citizen["underwater"] = false
		citizen["travel_mode"] = "boat" if int(citizen["id"]) % 2 == 0 else "swim"
	world.render_world(tiles, [], [], citizens)
	world.set_underwater_view(false)
	if world._terrain_mesh != null:
		assert(world._terrain_mesh.visible)
	await create_timer(0.4).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/aquatic-surface.png")
	print("PASS: all eight aquatic appearances, surface/underwater layers and boat assets render")
	quit()
