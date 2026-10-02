extends SceneTree

func _initialize() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	await process_frame
	renderer.configure_environment({
		"weather": "RAIN", "weather_intensity": 0.8,
		"wind_speed": 11.0, "wind_direction": 90.0,
		"feels_like_c": -6.0
	})
	renderer.render_world({
		Vector2i(0, 0): {"terrain": "grass"},
		Vector2i(1, 0): {"terrain": "water"}
	}, [
		{"id": "tree", "type": "tree", "x": 0, "y": 0, "growth": 1.0, "quantity": 40, "capacity": 40}
	])
	var motion_layer: WorldRenderer = renderer._dynamic_layer
	assert(motion_layer._weather == "RAIN")
	assert(motion_layer._wind_vector().x > 0.9)
	var before := motion_layer._visual_seconds
	await process_frame
	await process_frame
	assert(motion_layer._visual_seconds > before)
	renderer.set_simulation_running(false)
	var paused := motion_layer._visual_seconds
	await process_frame
	assert(is_equal_approx(motion_layer._visual_seconds, paused))
	print("PASS: shared environmental physics responds to weather and pauses")
	quit()
