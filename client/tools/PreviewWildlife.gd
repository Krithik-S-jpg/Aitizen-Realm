extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1000, 640)
	var renderer = load("res://scripts/world/WorldRenderer.gd").new()
	root.add_child(renderer)
	renderer.position = Vector2(500, 110)
	var tiles: Dictionary = {}
	for x: int in range(16):
		for y: int in range(16):
			tiles[Vector2i(x,y)] = {"terrain": "grass"}
	var animals: Array = []
	var species: Array[String] = ["deer", "rabbit", "boar", "wolf", "fox", "bear", "goat", "duck"]
	for index: int in range(species.size()):
		animals.append({"id": str(index), "kind": "animal", "x": 2 + index % 4 * 3, "y": 3 + index / 4 * 5, "action": "hunt", "metadata": {"species": species[index]}})
	renderer.render_world(tiles, [], [], animals)
	await create_timer(0.4).timeout
	renderer.set_simulation_running(false)
	var frozen: float = renderer._visual_seconds
	await create_timer(0.3).timeout
	assert(renderer._visual_seconds == frozen)
	for motion: Variant in renderer._entity_motion_amounts.values():
		assert(float(motion) == 0.0)
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/wildlife-paused.png")
	for animal: Dictionary in animals:
		animal["action"] = "sleep"
	renderer.update_entities(animals)
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/wildlife-sleep.png")
	print("PASS: pause freezes clock and movement; all wildlife rendered")
	quit()
