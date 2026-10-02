extends SceneTree


func _initialize() -> void:
	assert(WorldApiClient.sanitize_generation_options({"width": 4, "height": 900}) == {
		"width": 8, "height": 128, "avatar_id": "scout"
	})
	assert(WorldApiClient.generation_url("http://localhost/world", {
		"width": 96, "height": 64, "seed": 42
	}) == "http://localhost/world/generate?width=96&height=64&seed=42&player_avatar=scout")
	assert(WorldApiClient.generation_url("http://localhost/world", {
		"width": 32, "height": 32
	}) == "http://localhost/world/generate?width=32&height=32&player_avatar=scout")
	var panel := SimulationSettingsPanel.new()
	root.add_child(panel)
	await process_frame
	panel.open_panel({}, 1.0, {"width": 96, "height": 96, "seed": 1234})
	assert(panel._world_size.selected == 2)
	assert(panel._world_width.value == 96)
	assert(panel._world_height.value == 96)
	panel._random_seed.button_pressed = false
	panel._starter_avatar.select(7)
	assert(panel.world_generation_options() == {"width": 96, "height": 96, "seed": 1234, "avatar_id": "artisan"})
	panel._world_size.select(0)
	panel._on_world_size_selected(0)
	assert(panel.world_generation_options().width == 32)
	assert(panel.world_generation_options().height == 32)
	print("PASS: new-world settings, bounded requests, random/fixed seeds and presets")
	quit()
