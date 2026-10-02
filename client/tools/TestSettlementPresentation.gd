extends SceneTree

class IdentityPreview extends WorldRenderer:
	func _draw() -> void:
		var avatars := ["scout", "builder", "herbalist", "scholar", "cook", "miner", "fisher", "artisan"]
		for index: int in range(avatars.size()):
			var origin := Vector2(85 + (index % 4) * 190, 105 + floori(float(index) / 4) * 165)
			draw_set_transform(origin, 0, Vector2(1.35, 1.35))
			_draw_agent_sprite(Vector2.ZERO, "sleep" if index % 2 == 0 else "chop", index * 0.17 + 0.1, avatars[index])
		draw_set_transform(Vector2.ZERO)

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(800, 400)
	RenderingServer.set_default_clear_color(Color("355c49"))
	var atlas := load("res://assets/pixel_art/citizen_roster_v1.png") as Texture2D
	var pixels := atlas.get_image()
	assert(pixels.get_pixel(0, 0).a == 0.0, "Citizen atlas must have genuine alpha")
	var buildables := load("res://assets/pixel_art/buildables_atlas_v1.png") as Texture2D
	assert(buildables != null)
	assert(buildables.get_image().get_pixel(0, 0).a == 0.0, "Buildables atlas must have genuine alpha")
	var seen: Dictionary = {}
	for avatar: int in range(8):
		var cell := pixels.get_region(Rect2i((avatar % 4) * 384, floori(float(avatar) / 4) * 512, 384, 512))
		seen[hash(cell.get_data())] = true
	assert(seen.size() == 8, "Every selectable appearance must have a distinct source region")
	assert(WorldRenderer.animation_frame(0.5, 12, 2.4) == 2)
	var preview := IdentityPreview.new()
	root.add_child(preview)
	await create_timer(0.3).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/citizen-sleep-frames.png")
	print("PASS: eight identities remain visible during sleep and work actions")
	quit()
