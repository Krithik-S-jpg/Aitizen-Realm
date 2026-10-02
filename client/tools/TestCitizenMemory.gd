extends SceneTree

class SleepVisibility extends WorldRenderer:
	var drawn := 0
	func _draw_agent_sprite(_base: Vector2, _action: String, _phase: float, _avatar_id := "scout") -> void:
		drawn += 1
	func _draw() -> void:
		drawn = 0
		_draw_agent(Vector2.ZERO, {"action": "sleep", "indoors": true})
		assert(drawn == 0, "Indoor sleepers must be hidden")
		_draw_agent(Vector2.ZERO, {"action": "sleep", "indoors": false})
		assert(drawn == 1, "Outdoor sleepers must remain visible")

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var panel := preload("res://scripts/ui/CitizenMemoryView.gd").new()
	root.add_child(SleepVisibility.new())
	root.add_child(panel)
	panel.show_citizen({"name": "Witness", "fear": 45, "metadata": {"fear_memory_id": "event"}, "decision_reason": "Seek safety", "memory_graph": [{"id": "event", "tick": 10, "summary": "Witnessed a wolf attack", "x": 5, "y": 5, "importance": 0.85, "details": {"species": "wolf", "experience": "witnessed", "attacker_id": "wolf-1", "victim_id": "citizen-2", "fear_gain": 45, "consequence": "Avoid the attack location"}}]})
	assert(panel._graph.get_connection_list().size() == 4)
	assert(panel._serial == 5)
	if DisplayServer.get_name() != "headless":
		await create_timer(0.5).timeout
		await RenderingServer.frame_post_draw
		panel.get_texture().get_image().save_png("res://.agent-qa/citizen-memory-graph.png")
	panel.show_citizen({"name": "New citizen", "memory_graph": []})
	assert(panel._graph.get_connection_list().size() == 1)
	assert(panel._serial == 2)
	await process_frame
	await create_timer(0.2).timeout
	print("PASS: citizen memory tree exposes experience, cause, participants, fear and decision")
	quit()
