extends SceneTree


func _initialize() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	renderer.update_resources([{"id": "tree", "x": 3, "y": 3, "type": "tree"}])
	var entity := {"x": 2, "y": 3, "action_target": {"resource_id": "tree"}}
	assert(renderer.work_effect_origin(entity) == renderer.map_to_local(Vector2i(3, 3)))
	entity["x"] = 10
	assert(renderer.work_effect_origin(entity) == null, "No work effects from across the map")
	entity["x"] = 2
	renderer.update_resources([])
	assert(renderer.work_effect_origin(entity) == null, "No effects for missing resources")
	var theme_script := preload("res://scripts/ui/AtlasTheme.gd")
	var button := Button.new()
	root.add_child(button)
	theme_script.apply_to(button)
	theme_script.apply_to(button)
	assert(button.mouse_entered.get_connections().size() == 1, "No duplicate hover handlers")
	theme_script.reduced_motion = true
	theme_script.animate_button(button, true)
	assert(button.modulate == Color("bdebe1"))
	print("PASS: resource effect range, missing targets, idempotent UI and instant feedback")
	quit()
