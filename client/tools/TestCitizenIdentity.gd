extends SceneTree

func _initialize() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	for avatar in ["juniper", "rowan"]:
		for action in ["idle", "move", "sleep", "gather", "build", "swim", "cook", "hunt"]:
			var frames: Array = visuals.action_frames(avatar, action)
			assert(frames.size() == (2 if action == "hunt" else 4))
			for frame in frames:
				assert(frame[2] > 0 and frame[3] > 0)
		assert(visuals.texture(avatar).resource_path.contains(avatar))
	print("PASS: Juniper and Rowan have eight nonempty animation rows")
	quit()
