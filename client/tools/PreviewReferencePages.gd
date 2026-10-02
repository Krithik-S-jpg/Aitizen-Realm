extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _capture(label: String) -> void:
	await create_timer(0.35).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/reference-%s.png" % label)


func _run() -> void:
	root.size = Vector2i(1152, 648)
	var template: Node = load("res://scenes/Main.tscn").instantiate()
	var ui: CanvasLayer = template.get_node("UI")
	template.remove_child(ui)
	template.free()
	root.add_child(ui)
	await process_frame
	var admin = ui.get_node("AdminPanel")
	admin.open_page(64, 64)
	admin.display_agents([
		{"id": "fixture-one", "kind": "AGENT", "name": "Preview citizen", "x": 10, "y": 12, "profession": "FORAGER", "needs": {"health": 92, "energy": 71, "hunger": 30, "thirst": 20}, "action": "gather", "goal": "satisfy_hunger", "decision_reason": "Collect known food to satisfy hunger", "inventory": {"fruit": 3}},
		{"id": "fixture-two", "kind": "AGENT", "name": "Preview builder", "x": 8, "y": 9, "profession": "BUILDER", "needs": {"health": 85, "energy": 62}, "action": "build"}
	])
	admin._table.get_root().get_first_child().select(0)
	admin._inspect_selected()
	assert(admin._details.text.contains("Collect known food"))
	admin._search.text = "builder"
	admin._rebuild_table()
	assert(admin._table.get_root().get_child_count() == 1)
	admin._search.clear()
	admin._rebuild_table()
	assert(admin._avatar_buttons.size() == 8)
	admin._select_avatar("artisan")
	assert(admin._avatar_id == "artisan")
	await _capture("citizens")
	assert(root.get_visible_rect().encloses(admin._page.get_global_rect()))
	admin.close_page()
	var analysis = ui.get_node("AnalysisPanel")
	for mode: String in ["animals", "buildings", "research", "history", "settlements", "economy"]:
		analysis.open_mode(mode)
		analysis.display_observation({"groups": [{"name": "Preview group", "member_ids": ["one", "two"], "home_x": 10, "home_y": 12}], "economy": {"stock": {"wood": 24, "stone": 12}, "inventories": 2, "structures": 3, "completed_structures": 1}, "timeline": [{"tick": 8, "type": "construction", "summary": "Preview construction event"}], "experiments": [{"name": "Preview experiment", "seed": 42, "status": "DRAFT"}]})
		analysis._data["wildlife"] = [{"name": "Preview deer", "x": 8, "y": 12, "needs": {"health": 88}, "metadata": {"age_days": 32, "state": "graze", "age_stage": "adult", "home_x": 7, "home_y": 10, "lifestyle": "Grazes in open meadows and returns to forest cover."}}]
		analysis._data["buildings"] = [{"structure_type": "shelter", "x": 9, "y": 12, "progress": 18, "work_required": 35, "progress_ratio": 18.0 / 35.0, "materials_delivered": {"wood": 14}, "missing_materials": {"wood": 6, "stone": 5}, "bed_capacity": 4, "resident_ids": [], "fuel": 0, "stockpile": {"items": {"wood": 4}}}]
		analysis._data["metrics"] = [{"tick": 1, "population": 2}, {"tick": 2, "population": 2}, {"tick": 3, "population": 3}]
		analysis._data["settlements"] = [{"id": "camp", "name": "Riverside camp", "active_members": 5, "home_x": 8, "home_y": 9, "shortages": ["A campfire needs fuel"], "stock": {"wood": 12}, "carried": {"stone": 5}, "households": [{"bed_capacity": 4, "occupied_beds": 4, "available_beds": 0}], "beds_total": 4, "beds_available": 0, "jobs": [{"name": "Citizen one", "activity": "build", "reason": "Complete the shared shelter"}], "job_board": [{"status": "claimed", "job_type": "deliver_construction", "material": "stone", "reason": "Deliver stone to the shared shelter."}], "construction": [{"type": "shelter", "progress": 0.6, "funded": false, "missing_materials": {"stone": 5}}]}]
		analysis._render_data()
		if mode in ["animals", "buildings", "settlements"]:
			analysis._table.get_root().get_first_child().select(0)
			analysis._inspect_record()
			assert(not analysis._content.text.is_empty())
			if mode == "settlements":
				analysis._render_data()
				assert(analysis._content.text.contains("Complete the shared shelter"))
				assert(analysis._content.text.contains("4 total"))
				assert(analysis._content.text.contains("deliver_construction"))
		await _capture(mode)
		assert(root.get_visible_rect().encloses(analysis._panel.get_global_rect()))
	analysis.hide()
	var settings = ui.get_node("SimulationSettingsPanel")
	settings.open_panel({}, 1.0)
	await _capture("settings")
	assert(root.get_visible_rect().encloses(settings._panel.get_global_rect()))
	for width: int in [900, 1440]:
		root.size = Vector2i(width, 720)
		await process_frame
		await process_frame
		assert(root.get_visible_rect().encloses(settings._panel.get_global_rect()))
		settings.hide()
		admin.open_page(64, 64)
		await process_frame
		assert(root.get_visible_rect().encloses(admin._page.get_global_rect()))
		admin.close_page()
	var manager = ui.get_node("UIManager")
	manager._palette.open_search()
	manager._palette._search.text = "citizens"
	manager._palette._refresh()
	assert(manager._palette._results.get_child_count() == 1)
	manager._palette.hide()
	print("PASS: reference pages fit, citizen search and inspector work")
	quit()
