extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var designer := preload("res://scripts/ui/ScenarioDesigner.gd").new()
	assert(not designer.visible, "Designer must be hidden before entering the scene")
	root.add_child(designer)
	assert(not designer.visible, "Designer must not open on startup")
	designer.popup_centered_clamped(Vector2i(980, 680))
	assert(designer.visible)
	designer.close_requested.emit()
	assert(not designer.visible)
	designer.popup_centered_clamped(Vector2i(980, 680))
	designer.add_event({"id": "rain", "kind": "weather", "choice": "RAIN", "x": 3, "y": 3, "at_tick": 12})
	var document: Dictionary = designer.document()
	assert(document.objectives.size() == 1)
	assert(document.events[0].choice == "RAIN")
	designer._load_document(document)
	assert(designer.document() == document)
	await create_timer(.4).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		designer.get_texture().get_image().save_png("res://.agent-qa/scenario-designer.png")
		designer._events.get_parent().get_parent().current_tab = 1
		await RenderingServer.frame_post_draw
		designer.get_texture().get_image().save_png("res://.agent-qa/scenario-timeline.png")
	var response := {"scenarios": {}, "run": {"status": "running", "elapsed": 10, "objectives": {"survive": {"label": "Survive", "value": 10, "target": 48}}, "history": [{"tick": 10, "message": "Test event received"}]}}
	designer._operation = "get"
	designer._completed(HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray(), JSON.stringify(response).to_utf8_buffer())
	assert(designer._history.text.contains("Test event received"))
	designer._progress.get_parent().get_parent().current_tab = 2
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		designer.get_texture().get_image().save_png("res://.agent-qa/scenario-progress.png")
	print("PASS: scenario designer hidden startup, explicit open/close and form roundtrip")
	quit()
