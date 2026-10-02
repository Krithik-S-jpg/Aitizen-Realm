extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(800, 500)
	RenderingServer.set_default_clear_color(Color("172b28"))
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(400, 90)
	root.add_child(renderer)
	var tiles: Dictionary = {}
	for x: int in range(8):
		for y: int in range(8):
			tiles[Vector2i(x, y)] = {"terrain": "grass"}
	var citizens: Array = [
		{"id": "awake", "kind": "agent", "name": "Awake scale", "x": 2, "y": 3, "action": "idle", "tags": []},
		{"id": "asleep", "kind": "agent", "name": "Sleep scale", "x": 4, "y": 3, "action": "sleep", "tags": []},
	]
	renderer.render_world(tiles, [], [], citizens)
	await create_timer(0.4).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/citizen-sleep-world.png")
	print("PASS: sleeping citizen renders beside standing scale reference")
	quit()
