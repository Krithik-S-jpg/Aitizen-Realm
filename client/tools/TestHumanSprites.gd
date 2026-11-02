extends SceneTree

func _initialize() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	var texture: Texture2D = visuals.texture("scout")
	assert(texture.resource_path.ends_with("scout_human_v2.png"))
	var image := texture.get_image()
	assert(image.get_pixel(0, 0).a == 0)
	for action in ["idle", "move", "sleep", "gather", "build", "swim", "cook", "hunt", "carry", "mine", "chop"]:
		var frames: Array = visuals.action_frames("scout", action)
		assert(frames.size() >= 2, action)
		assert(visuals.texture("scout", action) == texture, action)
		for frame in frames:
			var rect := Rect2i(frame[0], frame[1], frame[2], frame[3])
			assert(Rect2i(Vector2i.ZERO, image.get_size()).encloses(rect))
			assert(image.get_region(rect).get_used_rect().has_area())
	assert(is_equal_approx(visuals.action_frames("scout", "idle")[0][3] * visuals.scale_for("scout", "idle"), 48))
	assert(visuals.has_native_action("scout", "swim"))
	assert(visuals.has_native_action("builder", "swim"))
	assert(visuals.portrait("scout").atlas == texture)
	print("PASS: Aster human identity, action bounds, alpha, scale and portrait")
	quit()
