extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	root.size = Vector2i(1152, 648)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(576, 64)
	root.add_child(renderer)
	var tiles: Dictionary = {}
	for x: int in range(64):
		for y: int in range(64):
			var terrain := "water" if (x + y) % 17 < 3 else ("forest" if (x * 3 + y) % 11 < 3 else "grass")
			tiles[Vector2i(x, y)] = {"terrain": terrain, "metadata": {"variant": (x + y) % 4}}
	var resources: Array = []
	for index: int in range(520):
		resources.append({
			"id": "resource-%d" % index,
			"type": "tree" if index % 3 else "stone",
			"x": index * 17 % 64,
			"y": index * 29 % 64,
			"growth": 1.0,
			"quantity": 50.0,
			"capacity": 50.0,
			"variant": index % 4
		})
	var entities: Array = []
	for index: int in range(48):
		entities.append({
			"id": "entity-%d" % index,
			"kind": "animal" if index % 2 == 0 else "agent",
			"avatar_id": WorldRenderer.CITIZEN_AVATAR_ORDER[(index / 2) % 8],
			"x": 6 + index % 12,
			"y": 6 + index / 12,
			"action": "wander",
			"metadata": {"species": "deer" if index % 2 else "rabbit"}
		})
	renderer.configure_environment({
		"weather": "RAIN", "weather_intensity": 0.8,
		"wind_speed": 12.0, "wind_direction": 75.0, "feels_like_c": 4.0
	})
	renderer.render_world(tiles, resources, [], entities)
	for _frame: int in range(60):
		await process_frame
	var started := Time.get_ticks_usec()
	var measured_frames := 300
	for _frame: int in range(measured_frames):
		if _frame % 12 == 0:
			for entity: Dictionary in entities:
				entity["x"] = int(entity["x"]) + (1 if _frame % 24 == 0 else -1)
			renderer.update_entities(entities)
		await process_frame
	var elapsed_seconds := float(Time.get_ticks_usec() - started) / 1_000_000.0
	var average_fps := measured_frames / maxf(elapsed_seconds, 0.001)
	print("PERF: dense 64x64 fixture %.1f FPS (%.2f ms/frame)" % [average_fps, 1000.0 / average_fps])
	print("PERF: process %.2f ms, draw calls %d" % [Performance.get_monitor(Performance.TIME_PROCESS) * 1000, int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))])
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/living-world-benchmark.png")
	assert(average_fps >= 55.0, "Dense renderer did not meet the 60 FPS frame budget")
	quit()
