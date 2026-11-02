extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var panel := AnalysisPanel.new()
	root.add_child(panel)
	panel.open_mode("expeditions")
	panel.display_observation({"expeditions": [{"id": "test", "member_names": ["Aster", "Juniper"], "phase": "returning", "destination": [5, 11], "reason": "Reached survey destination", "discoveries": {"one": ["resource"]}, "supplies": {"one": {"food": 2}}}]})
	var item = panel._table.get_root().get_first_child()
	assert(item.get_text(0).contains("Juniper"))
	item.select(0)
	panel._inspect_record()
	assert(panel._content.text.contains("newly observed"))
	print("PASS: expedition dashboard shows real party, supplies and discoveries")
	quit()
