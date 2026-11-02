extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 648)
	var scene := load("res://scenes/Main.tscn") as PackedScene
	var main := scene.instantiate()
	root.add_child(main)
	await process_frame
	var panel: AdminPanel = main.get_node("UI/AdminPanel")
	panel.open_page(64, 64)
	panel.display_agents([{"id": "test-diver", "name": "Expedition test", "kind": "agent", "x": 4, "y": 7,
		"avatar_id": "scout", "needs": {"health": 100, "energy": 82}, "metadata": {},
		"oxygen": 76, "depth": 5, "dive_phase": "gather", "dive_origin": [4, 5],
		"inventory": {"items": {"shell": 2}}, "marine_discoveries": {"4,7": {"x": 4, "y": 7}}}])
	panel._table.get_root().get_first_child().select(0)
	panel._inspect_selected()
	await create_timer(0.5).timeout
	assert(panel._details.text.contains("EXPEDITION"))
	assert(not main.get_node("UI/DepthControls").visible)
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/expedition-ui.png")
	print("PASS: expedition inspector and page visibility")
	quit()
