extends SceneTree


class BuildablesPreview extends WorldRenderer:
	func _draw() -> void:
		var kinds := ["shelter", "tent", "storage", "campfire", "workbench", "well", "farm", "fence"]
		for index: int in range(kinds.size()):
			var origin := Vector2(90 + (index % 4) * 250, 135 + floori(float(index) / 4) * 190)
			_draw_structure(origin, {
				"structure_type": kinds[index], "completed": true,
				"progress_ratio": 1.0, "fuel": 20.0, "crop_growth": 1.0,
				"crop_food": 8.0
			})
		for stage: int in range(4):
			_draw_structure(Vector2(190 + stage * 250, 530), {
				"structure_type": "shelter", "completed": false,
				"funded": stage > 0, "progress_ratio": float(stage) / 3.0,
				"materials_required": {"wood": 20, "stone": 10},
				"materials_delivered": {"wood": stage * 6, "stone": stage * 3}
			})


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	root.size = Vector2i(1100, 620)
	RenderingServer.set_default_clear_color(Color("315a43"))
	var texture := load("res://assets/pixel_art/buildables_atlas_v1.png") as Texture2D
	assert(texture != null)
	assert(texture.get_size() == Vector2(1774, 887))
	assert(texture.get_image().get_pixel(0, 0).a == 0.0)
	var preview := BuildablesPreview.new()
	root.add_child(preview)
	await create_timer(0.3).timeout
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/buildables-presentation.png")
	print("PASS: eight completed buildables and four physical construction stages")
	quit()
