extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 648)
	var main = load("res://scenes/Main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var panel = main.get_node("UI/AdminPanel")
	panel.open_page(64, 64)
	panel.display_agents([{"id": "profile-test", "name": "Rowan", "kind": "agent", "avatar_id": "rowan", "gender": "male", "diet": "omnivore", "x": 12, "y": 14, "goal": "build", "action": "gather", "decision_reason": "Collect wood for the shared shelter.", "needs": {"health": 76, "energy": 88, "hunger": 28, "thirst": 34}, "metadata": {}, "inventory": {"items": {"wood": 5}}}])
	panel._table.get_root().get_first_child().select(0)
	panel._table.item_selected.emit()
	await create_timer(0.5).timeout
	assert(panel._profile_page.visible)
	assert(panel._profile_name.text == "Rowan")
	assert(panel._profile_bars.health.bar.value == 76)
	assert(panel._profile_portrait.texture.atlas.resource_path.contains("rowan_actions_v2"))
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/citizen-profile.png")
	print("PASS: full citizen profile, live needs bars and male portrait")
	quit()
