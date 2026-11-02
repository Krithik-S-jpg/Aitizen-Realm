extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var world := preload("res://scenes/World.tscn").instantiate()
	world.position = Vector2(560, 130)
	root.add_child(world)
	var tiles := {}
	for x in range(12):
		for y in range(12):
			tiles[Vector2i(x, y)] = {"terrain": "water" if x > 7 else "grass", "metadata": {}}
	world.render_parsed_world({"tiles": tiles})
	world.configure_weather({"phase": "DAY", "weather": "RAIN", "weather_intensity": .5, "wind_speed": 12, "wind_direction": 90, "precipitation_radius": 8}, 12, 12)
	world.weather_overlay._display_intensity = .5
	assert(world._birds.anchors.size() > 0)
	assert(world._birds.target_activity == 1)
	await create_timer(1).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/rain-birds.png")
	world.scale = Vector2(1.5, 1.5)
	preload("res://scripts/ui/AtlasTheme.gd").reduced_motion = true
	var rain_time: float = world.weather_overlay._elapsed
	var bird_time: float = world._birds.elapsed
	await process_frame
	await process_frame
	assert(world.weather_overlay._elapsed == rain_time and world._birds.elapsed == bird_time)
	preload("res://scripts/ui/AtlasTheme.gd").reduced_motion = false
	await create_timer(.3).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/rain-birds-zoom.png")
	world.set_simulation_running(false)
	var time: float = world._birds.elapsed
	await process_frame
	assert(world._birds.elapsed == time)
	world.set_simulation_running(true)
	world.configure_weather({"phase": "DAY", "weather": "RAIN", "weather_intensity": 1}, 12, 12)
	assert(world._birds.target_activity == 0)
	world.renderer.set_underwater_view(true)
	await process_frame
	await process_frame
	assert(not world.weather_overlay.visible and not world._birds.visible)
	world.renderer.set_underwater_view(false)
	world.renderer.set_cave_view(true)
	await process_frame
	await process_frame
	assert(not world.weather_overlay.visible and not world._birds.visible)
	world.renderer.set_cave_view(false)
	world.set_visual_quality("performance")
	assert(world._birds.quality < .5)
	world.configure_weather({"phase": "NIGHT", "weather": "CLEAR"}, 12, 12)
	assert(world._birds.target_activity == 0)
	print("PASS: rain/birds render, habitat anchors, pause, quality, storms, night and hidden observation layers")
	quit()
