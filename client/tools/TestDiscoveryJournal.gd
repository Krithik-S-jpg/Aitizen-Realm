extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var panel := AnalysisPanel.new()
	root.add_child(panel)
	panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.open_mode("discoveries")
	panel.display_observation({"discovery_journal": [{"id": "first", "name": "Reedkeepers waystone", "kind": "inscription", "x": 5, "y": 8, "inspected": true, "next_id": "tower", "evidence": "A carved route points toward the broken watchtower.", "artifact": "Carved route tablet", "discoverers": [{"name": "Juniper", "tick": 14}], "accounts": [{"citizen": "Rowan", "confidence": 0.75, "source": "Juniper"}]}, {"id": "tower", "name": "Broken watchtower", "kind": "ruined_tower", "x": 14, "y": 6, "inspected": false, "discoverers": [{"name": "Rowan", "tick": 27}]}]})
	var item = panel._table.get_root().get_first_child()
	item.select(0)
	panel._inspect_record()
	assert(panel._content.text.contains("Juniper"))
	assert(panel._content.text.contains("75%"))
	assert(panel._discovery_map.visible)
	await create_timer(.6).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/discovery-journal.png")
	print("PASS: discovery journal evidence, illustrated map and provenance")
	quit()
