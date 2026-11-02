extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	renderer.position = Vector2(570, 170)
	var tiles := {}
	for x in range(8):
		for y in range(8):
			tiles[Vector2i(x, y)] = {"terrain": "grass", "metadata": {}}
	var birds := []
	# Real spawn payloads used to contain a biome string before the first tick.
	# Include old saves, missing/null homes, and established dens in the draw pass.
	for home_value: Variant in ["forest", null, {}, {"kind": "den", "x": 1, "y": 1, "status": "occupied"}]:
		birds.append({"id": "legacy%d" % birds.size(), "kind": "animal", "x": 1, "y": 1, "metadata": {"species": "wolf", "habitat": home_value}})
	var bird_offset := birds.size()
	for index in range(3):
		birds.append({"id": "bird%d" % index, "kind": "animal", "x": 2 + index, "y": 3, "metadata": {"species": "songbird", "altitude": index * 18, "state": "fly" if index == 2 else "perch", "habitat": {"kind": "nest", "x": 2 + index, "y": 3, "eggs": 1, "status": "occupied"}}})
	renderer.render_world(tiles, [], [], birds)
	await create_timer(.5).timeout
	birds[bird_offset + 2].metadata.altitude = 0
	renderer.update_entities(birds)
	await create_timer(.2).timeout
	var height: float = renderer._dynamic_layer._bird_heights.get("bird2", 0)
	assert(height > 0 and height < 36)
	await create_timer(1.6).timeout
	assert(is_zero_approx(float(renderer._dynamic_layer._bird_heights.get("bird2", -1))))
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/habitat-birds.png")
	renderer.hide()
	var panel := AnalysisPanel.new()
	root.add_child(panel)
	panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.open_mode("animals")
	panel.display_observation({"wildlife": [], "wildlife_journal": [{"species": "songbird", "kind": "nest", "observer": "Juniper", "x": 4, "y": 3, "first_seen_tick": 12, "last_seen_tick": 36, "status": "occupied", "eggs": 1}]})
	panel._table.get_root().get_first_child().select(0)
	panel._inspect_record()
	assert(panel._content.text.contains("Juniper"))
	assert(panel._content.text.contains("past observation"))
	panel.display_observation({"wildlife": [], "wildlife_journal": [{"id": "trail", "species": "deer", "kind": "migration_sightings", "observer": "Juniper", "x": 8, "y": 6, "points": [[2, 2], [3, 2], [5, 4], [8, 6]], "first_seen_tick": 12, "last_seen_tick": 36}]})
	panel._table.get_root().get_first_child().select(0)
	panel._inspect_record()
	assert(panel._migration_map.visible)
	assert(panel._migration_map.points.size() == 4)
	await create_timer(.4).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/wildlife-journal.png")
	print("PASS: simulated bird/nest rendering and observed journal detail")
	quit()
