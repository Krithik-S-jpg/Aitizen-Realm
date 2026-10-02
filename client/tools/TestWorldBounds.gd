extends SceneTree

## Headless regression for the renderer bounds used by world/camera helpers.
func _initialize() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	assert(renderer.get_used_rect() == Rect2i())
	renderer.render_world({
		Vector2i(-3, 4): {"terrain": "grass"},
		Vector2i(7, 9): {"terrain": "water"},
		Vector2i(2, 6): {"terrain": "forest"},
	})
	assert(renderer.get_used_rect() == Rect2i(-3, 4, 11, 6))
	print("PASS: renderer world bounds are valid")
	quit()
