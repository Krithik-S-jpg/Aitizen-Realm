extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var texture := load("res://assets/pixel_art/citizen_roster_v1.png") as Texture2D
	var image := texture.get_image()
	assert(image.get_size() == Vector2i(1536, 1024))
	assert(image.get_pixel(0, 0).a < 0.05)
	var panel := AdminPanel.new()
	root.add_child(panel)
	await process_frame
	assert(panel._avatar_buttons.size() == 8)
	panel._select_avatar("fisher")
	assert(panel._avatar_id == "fisher")
	assert(AdminPanel.CITIZEN_AVATARS[0].get("calling") == null, "Appearances must not imply gameplay roles")
	panel.display_agents([{
		"id": "layout-check", "kind": "AGENT", "name": "Nia", "x": 9, "y": 12,
		"avatar_id": "fisher", "action": "gather", "goal": "satisfy_hunger",
		"needs": {"health": 90, "energy": 70}, "metadata": {"state": "working"}
	}])
	var first_row := panel._table.get_root().get_first_child()
	assert(first_row.get_icon(0) == null, "The table must not expand full atlas cells as row icons")
	assert(first_row.get_text(0).contains("Nia"))
	var captured := {}
	panel.create_agent_requested.connect(func(agent_name: String, x: int, y: int, radius: int, autonomous: bool, avatar_id: String) -> void:
		captured["name"] = agent_name
		captured["x"] = x
		captured["y"] = y
		captured["radius"] = radius
		captured["autonomous"] = autonomous
		captured["avatar_id"] = avatar_id
	)
	panel._name_input.text = "Nia"
	panel._x_input.value = 9
	panel._y_input.value = 12
	panel._submit_agent()
	assert(captured == {"name": "Nia", "x": 9, "y": 12, "radius": 8, "autonomous": true, "avatar_id": "fisher"})
	print("PASS: role-free portraits, compact table rows, avatar selection and create payload")
	quit()
