extends Window

var _http: HTTPRequest
var _library: OptionButton
var _name: LineEdit
var _description: TextEdit
var _deadline: SpinBox
var _minimum: SpinBox
var _goals: VBoxContainer
var _events: VBoxContainer
var _progress: VBoxContainer
var _history: RichTextLabel
var _status: Label
var _entries := {}
var _selected := ""
var _revision := 0
var _busy := false
var _operation := ""
var _poll := 0.0
var _imported := {}
var _file: FileDialog
var _confirm: ConfirmationDialog
var _run := {}
var _export_report := false


func _init() -> void:
	# Windows do not inherit a hidden Control parent's visibility.
	visible = false


func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		hide()
		set_input_as_handled()


func _ready() -> void:
	title = "Scenario designer · Goals, timeline & live results"
	min_size = Vector2i(720, 480)
	close_requested.connect(hide)
	var background := ColorRect.new()
	background.color = Color("0d1929")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + edge, 16)
	add_child(margin)
	var column := VBoxContainer.new()
	margin.add_child(column)
	var heading := HBoxContainer.new()
	column.add_child(heading)
	label(heading, "SCENARIO DESIGNER")
	button(heading, "Close", hide)
	var toolbar := HBoxContainer.new()
	column.add_child(toolbar)
	_library = OptionButton.new()
	_library.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	toolbar.add_child(_library)
	button(toolbar, "Load", _load_selected)
	button(toolbar, "New", func(): _new_document())
	button(toolbar, "Duplicate", func(): _selected = ""; _revision = 0; _name.text += " copy")
	button(toolbar, "Delete loaded…", func():
		if _entries.has(_selected):
			_confirm.dialog_text = "Delete loaded design '%s'? World changes and run history are retained." % str(_entries[_selected].definition.name)
			_confirm.popup_centered()
		else:
			_status.text = "Load a saved design before deleting it.")
	_name = LineEdit.new()
	_name.placeholder_text = "Scenario name"
	column.add_child(_name)
	_description = TextEdit.new()
	_description.custom_minimum_size.y = 55
	_description.placeholder_text = "Briefing: what should happen?"
	column.add_child(_description)
	var limits := HBoxContainer.new()
	column.add_child(limits)
	label(limits, "Deadline ticks (0 = none)")
	_deadline = number(limits, 0, 1000000)
	label(limits, "Minimum living citizens")
	_minimum = number(limits, 0, 10000)
	var tabs := TabContainer.new()
	tabs.add_theme_stylebox_override("panel", preload("res://scripts/ui/AtlasTheme.gd").surface("102236"))
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(tabs)
	_goals = page(tabs, "Objectives")
	label(_goals, "All goals must be true together. Existing world progress counts. Inventory = carried + completed-building storage.")
	button(_goals, "+ Objective", func(): add_goal())
	_events = page(tabs, "Event timeline")
	label(_events, "Ticks are relative to Start. Events run once; optional goal ID gates execution. Weather lasts 48 ticks.")
	button(_events, "+ Event", func(): add_event())
	_progress = page(tabs, "Live progress")
	_history = RichTextLabel.new()
	_history.custom_minimum_size.y = 180
	_history.bbcode_enabled = false
	_progress.add_child(_history)
	var actions := HFlowContainer.new()
	column.add_child(actions)
	button(actions, "Validate", func(): _send("validate"))
	button(actions, "Save design", func(): _send("save"))
	button(actions, "Start saved", func(): _send("start"))
	button(actions, "Stop", func(): _send("stop"))
	button(actions, "Refresh", func(): _send("get"))
	button(actions, "Import…", func(): _choose_file(false))
	button(actions, "Export…", func(): _choose_file(true))
	button(actions, "Export results…", func(): _choose_file(true, true))
	_status = Label.new()
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.text = "Pause before saving/starting. Start runs the SAVED design on this world; it does not reset the world."
	column.add_child(_status)
	_http = HTTPRequest.new()
	_http.timeout = 15
	add_child(_http)
	_http.request_completed.connect(_completed)
	_file = FileDialog.new()
	_file.access = FileDialog.ACCESS_FILESYSTEM
	_file.filters = PackedStringArray(["*.json ; Scenario JSON"])
	add_child(_file)
	_file.file_selected.connect(_file_selected)
	_confirm = ConfirmationDialog.new()
	_confirm.dialog_text = "Delete this saved scenario design? The world and current run history are retained."
	add_child(_confirm)
	_confirm.confirmed.connect(func(): _send("delete"))
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(margin)
	_new_document()
	_description.add_theme_stylebox_override("normal", preload("res://scripts/ui/AtlasTheme.gd").surface("091320"))


func button(parent: Node, text: String, callback: Callable) -> void:
	var control := Button.new()
	control.text = text
	control.pressed.connect(callback)
	parent.add_child(control)


func label(parent: Node, text: String) -> void:
	var control := Label.new()
	control.text = text
	control.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(control)


func number(parent: Node, value: float, maximum: float) -> SpinBox:
	var control := SpinBox.new()
	control.max_value = maximum
	control.value = value
	control.custom_minimum_size.x = 85
	parent.add_child(control)
	return control


func text_field(parent: Node, value: String, hint: String) -> LineEdit:
	var control := LineEdit.new()
	control.text = value
	control.placeholder_text = hint
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(control)
	return control


func choices(parent: Node, items: Array, value: String) -> OptionButton:
	var control := OptionButton.new()
	for item in items:
		control.add_item(item)
		if item == value:
			control.select(control.item_count - 1)
	parent.add_child(control)
	return control


func page(tabs: TabContainer, caption: String) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.name = caption
	tabs.add_child(scroll)
	var content := VBoxContainer.new()
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_theme_constant_override("separation", 10)
	scroll.add_child(content)
	return content


func add_goal(data: Dictionary = {}) -> void:
	var row := VBoxContainer.new()
	_goals.add_child(row)
	var top := HBoxContainer.new()
	row.add_child(top)
	var id := text_field(top, str(data.get("id", "goal_" + str(Time.get_ticks_usec()))), "Unique goal ID")
	var caption := text_field(top, str(data.get("label", "Survive")), "Goal title")
	button(top, "Remove", func(): row.free())
	var bottom := HBoxContainer.new()
	row.add_child(bottom)
	var metric := choices(bottom, ["elapsed", "population", "structures", "inventory", "explored"], str(data.get("metric", "elapsed")))
	var target := number(bottom, float(data.get("target", 48)), 1000000)
	var subject := text_field(bottom, str(data.get("subject", "")), "Item (wood), structure (SHELTER), or blank")
	row.set_meta("collect", func() -> Dictionary: return {"id": id.text, "label": caption.text, "metric": metric.get_item_text(metric.selected), "target": target.value, "subject": subject.text})
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(row)


func add_event(data: Dictionary = {}) -> void:
	var row := VBoxContainer.new()
	_events.add_child(row)
	var top := HBoxContainer.new()
	row.add_child(top)
	var id := text_field(top, str(data.get("id", "event_" + str(Time.get_ticks_usec()))), "Unique event ID")
	var tick := number(top, float(data.get("at_tick", 12)), 1000000)
	tick.tooltip_text = "Ticks after scenario start"
	var gate := text_field(top, str(data.get("after_objective", "")), "Optional goal ID prerequisite")
	button(top, "Remove", func(): row.free())
	var middle := HBoxContainer.new()
	row.add_child(middle)
	var kind := choices(middle, ["message", "resource", "weather"], str(data.get("kind", "message")))
	var choice := choices(middle, ["", "TREE", "STONE", "BUSH", "HERB", "ORE", "RAIN", "SNOW", "CLEAR"], str(data.get("choice", "")))
	label(middle, "X / Y / radius")
	var x := number(middle, float(data.get("x", 0)), 100000)
	var y := number(middle, float(data.get("y", 0)), 100000)
	var radius := number(middle, float(data.get("radius", 0)), 2)
	var blocked := choices(middle, ["skip", "fail"], str(data.get("on_blocked", "skip")))
	blocked.tooltip_text = "If placement is blocked: skip event or fail scenario"
	var message := text_field(row, str(data.get("message", "")), "Message text (message events)")
	row.set_meta("collect", func() -> Dictionary: return {"id": id.text, "at_tick": int(tick.value), "after_objective": gate.text, "kind": kind.get_item_text(kind.selected), "choice": choice.get_item_text(choice.selected), "x": int(x.value), "y": int(y.value), "radius": int(radius.value), "on_blocked": blocked.get_item_text(blocked.selected), "message": message.text})
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(row)


func document() -> Dictionary:
	var goals: Array = []
	var events: Array = []
	for row in _goals.get_children():
		if row.has_meta("collect"):
			goals.append(row.get_meta("collect").call())
	for row in _events.get_children():
		if row.has_meta("collect"):
			events.append(row.get_meta("collect").call())
	return {"schema_version": 1, "name": _name.text, "description": _description.text, "deadline": int(_deadline.value), "minimum_population": int(_minimum.value), "objectives": goals, "events": events}


func _new_document() -> void:
	_selected = ""
	_revision = 0
	_load_document({"name": "New scenario", "objectives": [{"id": "survive", "label": "Survive 48 ticks", "metric": "elapsed", "target": 48}]})


func _load_document(data: Dictionary) -> void:
	_name.text = str(data.get("name", ""))
	_description.text = str(data.get("description", ""))
	_deadline.value = float(data.get("deadline", 0))
	_minimum.value = float(data.get("minimum_population", 0))
	for content in [_goals, _events]:
		for row in content.get_children():
			if row.has_meta("collect"):
				row.free()
	for goal in data.get("objectives", []):
		add_goal(goal)
	for event in data.get("events", []):
		add_event(event)


func _load_selected() -> void:
	if _library.selected < 0:
		return
	_selected = str(_library.get_item_metadata(_library.selected))
	_revision = int(_entries[_selected].revision)
	_load_document(_entries[_selected].definition)


func _send(operation: String) -> void:
	if _busy:
		return
	if operation == "start" and (not _entries.has(_selected) or document() != _entries[_selected].definition):
		_status.text = "Save your current design before starting it."
		return
	_operation = operation
	var payload := {"operation": operation, "scenario_id": _selected, "revision": _revision}
	if operation in ["save", "validate"]:
		payload["definition"] = _imported if not _imported.is_empty() else document()
	_busy = true
	if operation != "get":
		_lock_form(true)
	var error := _http.request(RuntimeConfig.http_url("/api/v1/world/scenarios"), PackedStringArray(["Content-Type: application/json"]), HTTPClient.METHOD_GET if operation == "get" else HTTPClient.METHOD_POST, "" if operation == "get" else JSON.stringify(payload))
	if error != OK:
		_busy = false
		_lock_form(false)
		_status.text = "Could not send request."


func _completed(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_busy = false
	_lock_form(false)
	var data: Variant = JSON.parse_string(body.get_string_from_utf8())
	if result != HTTPRequest.RESULT_SUCCESS or code >= 400 or not data is Dictionary:
		_status.text = str(data.get("detail", "Request failed; refresh before retrying.")).left(600) if data is Dictionary else "Connection failed."
		_imported.clear()
		return
	_entries = data.get("scenarios", {})
	_library.clear()
	for id in _entries:
		_library.add_item(str(_entries[id].definition.name))
		_library.set_item_metadata(_library.item_count - 1, id)
		if id == _selected:
			_library.select(_library.item_count - 1)
	if _operation == "save":
		_selected = str(data.selected)
		_revision = int(_entries[_selected].revision)
	if _operation == "delete":
		_selected = ""
		_revision = 0
	for index in range(_library.item_count):
		if _library.get_item_metadata(index) == _selected:
			_library.select(index)
	if _operation == "validate" and not _imported.is_empty():
		_selected = ""
		_revision = 0
		_load_document(_imported)
		_imported.clear()
	if _operation != "get":
		_status.text = _operation.capitalize() + " confirmed. Save world to persist the library and run."
	var run: Dictionary = data.get("run", {})
	_run = run
	for row in _progress.get_children():
		if row != _history:
			row.free()
	label(_progress, "%s · elapsed %s ticks" % [str(run.get("status", "Not started")).to_upper(), str(run.get("elapsed", 0))])
	for goal: Dictionary in run.get("objectives", {}).values():
		label(_progress, "%s: %s / %s" % [goal.label, goal.value, goal.target])
		var bar := ProgressBar.new()
		bar.max_value = float(goal.target)
		bar.value = float(goal.value)
		_progress.add_child(bar)
	var lines := PackedStringArray()
	for entry: Dictionary in run.get("history", []):
		lines.append("Tick %s · %s" % [str(entry.tick), str(entry.message)])
	_history.text = "\n".join(lines)
	_progress.move_child(_history, _progress.get_child_count()-1)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(_progress)


func _lock_form(locked: bool, node: Node = self) -> void:
	if node is Button:
		node.disabled = locked
	elif node is LineEdit or node is TextEdit or node is SpinBox:
		node.editable = not locked
	for child in node.get_children():
		_lock_form(locked, child)


func _process(delta: float) -> void:
	if not visible:
		return
	_poll += delta
	if _poll >= 3.0 and not _busy:
		_poll = 0
		_send("get")


func _choose_file(save_file: bool, report: bool = false) -> void:
	_export_report = report
	_file.file_mode = FileDialog.FILE_MODE_SAVE_FILE if save_file else FileDialog.FILE_MODE_OPEN_FILE
	_file.current_file = ("scenario-results.json" if report else "scenario.json") if save_file else ""
	_file.popup_centered_ratio(.7)


func _file_selected(path: String) -> void:
	if _file.file_mode == FileDialog.FILE_MODE_SAVE_FILE:
		var file := FileAccess.open(path, FileAccess.WRITE)
		if file:
			file.store_string(JSON.stringify(_run if _export_report else document(), "\t"))
			_status.text = "Results exported." if _export_report else "Design exported (not a world snapshot)."
		else:
			_status.text = "Unable to write file."
	else:
		var file := FileAccess.open(path, FileAccess.READ)
		if not file or file.get_length() > 262144:
			_status.text = "Cannot read file or file exceeds 256 KB."
			return
		var data: Variant = JSON.parse_string(file.get_as_text())
		if not data is Dictionary or _busy:
			_status.text = "Invalid JSON or request busy; retry shortly."
			return
		_imported = data
		_send("validate")
