extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1100, 720)
	var world := WorldRenderer.new()
	world.position = Vector2(550, 100)
	root.add_child(world)
	var tiles := {}
	for x in range(16):
		for y in range(16):
			tiles[Vector2i(x, y)] = {"terrain": "ocean" if x > 7 else "water", "metadata": {}}
	tiles[Vector2i(0, 0)].terrain = "ice"
	tiles[Vector2i(1, 0)].terrain = "sand"
	world.render_world(tiles, [], [], [])
	world.configure_environment({"wind_speed": 0, "weather": "CLEAR"})
	var calm := world.water_wave_strength(Vector2i(12, 8))
	assert(calm > world.water_wave_strength(Vector2i(0, 1)))
	assert(world.water_wave_strength(Vector2i(0, 0)) == 0)
	world.configure_environment({"wind_speed": 20, "weather": "RAIN", "weather_intensity": 1})
	assert(world.water_wave_strength(Vector2i(12, 8)) > calm)
	await create_timer(.6).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/waves.png")
	print("PASS: wave exposure, wind/weather response and frozen-water exclusion")
	quit()
