extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1000, 700)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(480, 160)
	root.add_child(renderer)
	var tiles := {}
	for x in range(8):
		for y in range(8):
			tiles[Vector2i(x, y)] = {"terrain": "grass"}
	var entities := []
	for index in range(3):
		entities.append({"id": "carrier%d" % index, "kind": "agent", "name": "Rescuer", "x": index * 2, "y": 2, "avatar_id": ["rowan", "juniper", "scout"][index], "carrying_casualty": "patient%d" % index, "carried_avatar": ["juniper", "rowan", "scout"][index], "action": "move", "metadata": {}})
	renderer.render_world(tiles, [], [], entities)
	await create_timer(.5).timeout
	for entity: Dictionary in renderer._dynamic_layer._entities:
		renderer._dynamic_layer._entity_motion_amounts[str(entity.id)] = 1.0
	await create_timer(.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/rescue-carry.png")
	for entity: Dictionary in entities:
		entity["underwater"] = true
	for tile: Vector2i in tiles:
		tiles[tile] = {"terrain": "water", "metadata": {"marine": {"depth": 2}}}
	renderer.render_world(tiles, [], [], entities)
	renderer.set_underwater_view(true)
	await create_timer(.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/rescue-tow.png")
	print("PASS: carry and tow render for Rowan, Juniper and classic appearances")
	quit()
