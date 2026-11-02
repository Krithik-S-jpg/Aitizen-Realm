extends SceneTree

func _initialize() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	for action in ["carry_infant", "cradle", "teach"]:
		var frames: Array = visuals.action_frames("scout", action)
		assert(frames.size() == 4)
		var texture: Texture2D = visuals.texture("scout", action)
		var image := texture.get_image()
		assert(image.get_pixel(0, 0).a == 0)
		for frame in frames:
			assert(frame[2] > 0 and frame[3] > 0)
			assert(Rect2i(Vector2i.ZERO, image.get_size()).encloses(Rect2i(frame[0], frame[1], frame[2], frame[3])))
	assert(not visuals.has_native_action("builder", "teach"))
	print("PASS: dedicated Aster care frames, alpha and identity isolation")
	quit()
