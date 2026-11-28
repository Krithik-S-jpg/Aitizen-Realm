extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size=Vector2i(1200,650)
	root.add_child(load("res://tools/AdultAnimationPreview.gd").new())
	for frame: int in range(180):
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/adult-animation-preview.png")
	quit()
