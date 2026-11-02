extends SceneTree

func _initialize() -> void:
	call_deferred("_test")

func _test() -> void:
	var scene := load("res://scenes/Main.tscn") as PackedScene
	var main := scene.instantiate()
	root.add_child(main)
	await process_frame
	var controls: Control = main.get_node("UI/DepthControls")
	var hud: Node = main.get_node("UI/DebugPanel")
	assert(controls.visible, "Depth controls should appear in World")
	for mode: String in ["settings", "citizens", "build", "research", "history", "settlements", "economy"]:
		hud.navigation_requested.emit(mode)
		assert(not controls.visible, "Depth controls overlap page: " + mode)
		hud.navigation_requested.emit("world")
		await create_timer(0.35).timeout
		assert(controls.visible, "Depth controls should return in World")
	hud.focus_mode_requested.emit(true)
	assert(not controls.visible, "World focus should hide depth controls")
	hud.focus_mode_requested.emit(false)
	assert(controls.visible)
	print("PASS: depth controls hidden on pages and world focus, restored in World")
	quit()
