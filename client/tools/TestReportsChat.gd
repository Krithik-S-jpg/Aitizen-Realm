extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var report = load("res://scripts/ui/SimulationReport.gd").new()
	root.add_child(report)
	report.generate({"timeline": [{"tick": 25, "type": "construction", "summary": "Shelter finished"}]})
	assert(report.report_text.contains("Shelter finished"))
	assert(report.report_text.contains("25"))
	report.hide()
	var chat = load("res://scripts/ui/CitizenDirectChat.gd").new()
	root.add_child(chat)
	chat.open_citizen({"id": "test", "name": "Rowan"})
	assert(chat.owner_id == "test")
	assert(chat.log_view.text.contains("Rowan"))
	print("PASS: report generation and direct chat UI")
	quit()
