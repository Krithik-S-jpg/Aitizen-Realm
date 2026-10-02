extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	await process_frame
	var pixels := renderer._sprite_atlas.get_image()
	for action: String in ["move", "chop", "mine", "gather", "build"]:
		var frames: Array = renderer._agent_sprite_regions[action]
		var distinct := {}
		for values: Array in frames:
			var cell := pixels.get_region(Rect2i(values[0], values[1], values[2], values[3]))
			distinct[hash(cell.get_data())] = true
		assert(distinct.size() > 1, action + " requires distinct source frames")
		assert(WorldRenderer.animation_frame(0.0, frames.size(), 0.8) != WorldRenderer.animation_frame(0.45, frames.size(), 0.8))
	print("PASS: distinct walking and tool frames with frame-based playback")
	quit()
