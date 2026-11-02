extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("FPS benchmark requires an actual rendering window")
		quit(1)
		return
	root.size = Vector2i(1500, 1500)
	var preview = load("res://tools/HumanAnimationPreview.gd").new()
	root.add_child(preview)
	var samples: Array[float] = []
	var last := Time.get_ticks_usec()
	for frame in range(360):
		preview.sample_time = frame / 60.0
		await process_frame
		var now := Time.get_ticks_usec()
		if frame >= 60:
			samples.append((now-last)/1000.0)
		last = now
	samples.sort()
	print(JSON.stringify({"fixture": "character atlas matrix, not full world", "frames": samples.size(), "median_frame_ms": samples[150], "p95_frame_ms": samples[285], "worst_frame_ms": samples.back(), "renderer": RenderingServer.get_video_adapter_name()}))
	quit()
