extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 648)
	var panel := AdminPanel.new()
	root.add_child(panel)
	panel.display_agents([{"id": "one", "kind": "agent", "name": "Aster", "ai_mode": "local_llm", "metadata": {"conversation": [
		{"sender": "Aster", "recipient": "Fern", "content": "Here, take 2 food.", "tick": 10},
		{"sender": "Fern", "recipient": "Aster", "content": "Thank you for sharing!", "tick": 10}]}}])
	panel._table.get_root().get_first_child().select(0)
	panel._inspect_selected()
	panel._open_conversations()
	assert(panel._table.get_root().get_first_child().get_text(5) == "Local LLM")
	assert(panel._chat_messages.get_child_count() == 2)
	assert(panel._chat_messages.get_child(0).get_child(0) is not PanelContainer)
	assert(panel._chat_messages.get_child(1).get_child(0) is PanelContainer)
	assert(panel._chat_threads.item_count == 2)
	assert(panel._chat_seen.size() == 2)
	panel._chat_peer = "Fern"
	panel._chat_signature = ""
	panel._update_conversation_text()
	assert(panel._chat_messages.get_child_count() == 2)
	var overlay := WorldEventOverlay.new()
	root.add_child(overlay)
	var event := {"id": "test", "event_type": "construction", "severity": "success", "title": "Shelter completed"}
	overlay.display_events([event, event, {"id": "sleep", "event_type": "sleep"}])
	assert(overlay._stack.get_child_count() == 1)
	if DisplayServer.get_name() != "headless":
		await create_timer(0.5).timeout
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://.agent-qa/community-chat.png")
	await create_timer(5.15).timeout
	assert(overlay._stack.get_child_count() == 0)
	print("PASS: chat bubbles, AI badge, event filtering/deduplication and five-second expiry")
	quit()
