extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(690, 240)
	root.add_child(renderer)
	var tiles := {}
	for x in range(8):
		for y in range(8):
			tiles[Vector2i(x,y)] = {"terrain": "grass", "metadata": {}}
	renderer.render_world(tiles)
	var layer := CanvasLayer.new()
	root.add_child(layer)
	var editor := preload("res://scripts/ui/WorldEditor.gd").new()
	editor.renderer = renderer
	layer.add_child(editor)
	for child in editor.get_children():
		if child is Window:
			assert(not child.visible, "Editor child windows must start hidden")
	editor.show()
	editor._brush = {"tiles": [{"x": 3, "y": 3}, {"x": 3, "y": 4}], "can_apply": true}
	editor._outline.queue_redraw()
	assert(editor._terrain.item_count == 7)
	assert(editor._radius.item_count == 3)
	assert(editor._tool.item_count == 4)
	editor._change_tool(1)
	assert(editor._terrain.item_count == 5)
	editor._change_tool(2)
	editor._tool.select(2)
	assert(editor._terrain.item_count == 3)
	var weather := WeatherOverlay.new()
	weather.renderer = renderer
	renderer.add_child(weather)
	weather.set_patches([{"x": 3, "y": 3, "radius": 2, "weather": "RAIN", "intensity": .85}])
	assert(not weather._allows_point(renderer.map_to_local(Vector2i(3, 3))))
	weather._drawing_patch = 0
	assert(weather._allows_point(renderer.map_to_local(Vector2i(3, 3))))
	await create_timer(.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/world-editor.png")
	editor.hide()
	assert(editor._brush.is_empty() and not editor._outline.visible)
	print("PASS: world editor controls, preview overlay and close cleanup")
	quit()
