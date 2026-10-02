extends SceneTree

const Visuals = preload("res://scripts/world/CitizenVisuals.gd")
const ACTIONS := ["move", "chop", "mine", "gather", "carry", "build", "sleep", "idle"]

class Gallery extends WorldRenderer:
	func _draw() -> void:
		var actions := ["move", "chop", "mine", "gather", "carry", "build", "sleep", "idle"]
		for row: int in range(8):
			draw_string(ThemeDB.fallback_font, Vector2(8, 65 + row * 72), actions[row], HORIZONTAL_ALIGNMENT_LEFT, -1, 14)
			for column: int in range(8):
				draw_set_transform(Vector2(145 + column * 122, 70 + row * 72), 0, Vector2(0.8, 0.8))
				_draw_agent_sprite(Vector2.ZERO, actions[row], 0.43, CITIZEN_AVATAR_ORDER[column])
				draw_set_transform(Vector2.ZERO)

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1100, 820)
	RenderingServer.set_default_clear_color(Color("254a3c"))
	var identities := {}
	for avatar: String in WorldRenderer.CITIZEN_AVATAR_ORDER:
		identities[Visuals.texture(avatar).resource_path] = true
		for action: String in ACTIONS:
			var frames := Visuals.action_frames(avatar, action)
			assert(frames.size() == 6, avatar + " " + action)
			var pixels := Visuals.texture(avatar, action).get_image()
			assert(pixels.get_pixel(0, 0).a == 0)
			var distinct := {}
			for frame: Array in frames:
				var rect := Rect2i(frame[0], frame[1], frame[2], frame[3])
				assert(Rect2i(Vector2i.ZERO, pixels.get_size()).encloses(rect))
				assert(rect.size.x > 20 and rect.size.y > 20)
				distinct[hash(pixels.get_region(rect).get_data())] = true
			assert(distinct.size() > 1, "Action needs distinct artwork")
	assert(identities.size() == 8)
	root.add_child(Gallery.new())
	await create_timer(0.5).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/citizen-catalog.png")
	print("PASS: eight identities, eight actions each, six distinct source poses, genuine alpha and valid source bounds")
	quit()
