extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var overlay := WorldEventOverlay.new()
	root.add_child(overlay)
	var events: Array = []
	for index: int in range(20):
		events.append({"id": str(index), "title": "Test event", "tick": index})
	overlay.display_events(events)
	assert(overlay._stack.get_child_count() == 5, "Burst must leave five cards without freezing")
	assert(overlay._stack.get_child(0).text.contains("00019"))
	overlay.display_events(events)
	assert(overlay._stack.get_child_count() == 5, "Duplicate events must not create cards")
	await process_frame
	await process_frame
	overlay.queue_free()
	await process_frame
	print("World event overlay burst regression passed")
	quit()
