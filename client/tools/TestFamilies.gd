extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	for avatar in ["family_infant", "family_toddler_male", "family_toddler_female", "family_child_male", "family_child_female", "family_teen_male", "family_teen_female", "family_elder_male", "family_elder_female"]:
		var frames: Array = visuals.action_frames(avatar, "move")
		assert(frames.size() == 2)
		for frame: Array in frames:
			assert(frame[2] > 0 and frame[3] > 0)
		assert(visuals.scale_for(avatar, "move") > 0)
	var view = load("res://scripts/ui/FamilyTreeView.gd").new()
	root.add_child(view)
	var mother := {"id": "m", "name": "Mother", "metadata": {"life_stage": "adult"}}
	var child := {"id": "c", "name": "Child", "metadata": {"life_stage": "infant", "parent_ids": ["m"]}}
	view.show_family(child, [mother, child])
	await process_frame
	assert(view.visible)
	for node in view.get_children():
		if node is GraphEdit:
			assert(node.get_connection_list().size() == 1)
	print("PASS: life-stage atlas frames and connected family tree")
	quit()
