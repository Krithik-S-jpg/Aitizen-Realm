extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var template = load("res://scenes/Main.tscn").instantiate()
	var inspector = template.get_node("UI/TileInspector")
	inspector.get_parent().remove_child(inspector)
	template.free()
	root.add_child(inspector)
	var animal := {"id": "deer-1", "kind": "animal", "name": "Deer", "x": 2, "y": 3, "metadata": {"species": "deer"}, "needs": null, "inventory": null, "action": "graze"}
	inspector.display_entity_info(animal, 16)
	assert(inspector.label_title.text.begins_with("Deer"))
	assert(inspector.label_terrain.text.contains("Unavailable"))
	animal["action"] = "sleep"
	inspector.refresh_entities([animal], 16)
	assert(inspector.label_chunk.text.contains("SLEEP"))
	inspector.refresh_entities([], 16)
	assert(inspector.label_chunk.text.contains("No longer present"))
	inspector.hide_inspector()
	inspector.refresh_entities([animal], 16)
	assert(not inspector.panel.visible)
	print("PASS: live inspector updates, missing data, disappearance and close")
	quit()
