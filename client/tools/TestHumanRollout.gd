extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	var catalog: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://config/citizen_human_actions.json"))
	for avatar: String in catalog:
		for action: String in catalog[avatar].actions:
			var texture: Texture2D = visuals.texture(avatar, action)
			assert(texture != null)
			var image := texture.get_image()
			for frame: Array in visuals.action_frames(avatar, action):
				var rect := Rect2i(frame[0], frame[1], frame[2], frame[3])
				assert(Rect2i(Vector2i.ZERO, image.get_size()).encloses(rect), avatar + action)
				assert(image.get_region(rect).get_used_rect().has_area(), avatar + action)
		assert(visuals.portrait(avatar).atlas == visuals.texture(avatar))
	if DisplayServer.get_name() != "headless":
		var canvas := SubViewport.new()
		canvas.size = Vector2i(1500, 1500)
		canvas.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		root.add_child(canvas)
		var preview = load("res://tools/HumanAnimationPreview.gd").new()
		canvas.add_child(preview)
		DirAccess.make_dir_recursive_absolute("res://.agent-qa")
		for i in range(4):
			preview.sample_time = i * 0.3
			preview.queue_redraw()
			await process_frame
			await RenderingServer.frame_post_draw
			assert(canvas.get_texture().get_image().save_png("res://.agent-qa/human-animation-%d.png" % i) == OK)
	print("PASS: all human manifests, action textures, frame bounds and portraits")
	quit()
