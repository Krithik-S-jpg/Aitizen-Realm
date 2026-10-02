extends SceneTree


func _initialize() -> void:
	var panel := PanelContainer.new()
	var button := Button.new()
	panel.add_child(button)
	root.add_child(panel)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(panel)
	assert(panel.get_theme_stylebox("panel") is StyleBoxFlat)
	assert(button.get_theme_stylebox("hover").border_color == Color("76d3c0"))
	assert(WorldRenderer.ANIMATION_FPS == 24.0)
	assert(WorldRenderer.animation_frame(0.0, 4, 1.0) == 0)
	assert(WorldRenderer.animation_frame(0.25, 4, 1.0) == 1)
	assert(WorldRenderer.animation_frame(0.75, 4, 1.0) == 3)
	assert(WorldRenderer.animation_frame(1.0, 4, 1.0) == 0)
	print("PASS: Atlas panel/button styling and 24 FPS animation contract")
	quit()
