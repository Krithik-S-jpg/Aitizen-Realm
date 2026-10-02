extends VBoxContainer

signal world_restored()
signal pause_requested()

var _request: HTTPRequest
var _status: Label
var _connection: Label
var _token: LineEdit
var _label: LineEdit
var _saves: OptionButton
var _buttons: Array[Button] = []
var _operation := ""
var _restore_id := ""
var _confirmation: ConfirmationDialog
var _cancel: Button
var _watchdog: Timer
var _archive: CheckBox
var _overwrite_confirmation: ConfirmationDialog
var _overwrite_id := ""
var _overwrite_archive := false

func _ready() -> void:
	add_theme_constant_override("separation", 10)
	var heading := Label.new()
	heading.text = "WORLD SAVES / SUPABASE"
	add_child(heading)
	_connection = Label.new()
	_connection.text = "SUPABASE · NOT CHECKED"
	_connection.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_connection)
	_status = Label.new()
	_status.text = "Not checked · enter your backend admin token, then Check connection."
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_status)
	_token = LineEdit.new()
	_token.secret = true
	_token.placeholder_text = "Backend CHECKPOINT_ADMIN_TOKEN (session only; never your Supabase key)"
	add_child(_token)
	_label = LineEdit.new()
	_label.placeholder_text = "Save name, e.g. Before winter"
	_label.max_length = 120
	add_child(_label)
	_archive = CheckBox.new()
	_archive.text = "Include research, metrics and event history (complete save)"
	_archive.button_pressed = true
	add_child(_archive)
	var actions := HFlowContainer.new()
	add_child(actions)
	_button(actions, "Check connection", func() -> void: _send("status", "/status"))
	_button(actions, "Pause world", func() -> void: pause_requested.emit())
	_button(actions, "Save as new", func() -> void:
		var title := _label.text.strip_edges()
		_send("save", "", HTTPClient.METHOD_POST, {"label": title if not title.is_empty() else "Manual world save", "include_archive": _archive.button_pressed}))
	_button(actions, "Refresh saves", func() -> void: _send("list", ""))
	_cancel = Button.new()
	_cancel.text = "Cancel request"
	_cancel.disabled = true
	_cancel.pressed.connect(_cancel_request)
	actions.add_child(_cancel)
	_saves = OptionButton.new()
	_saves.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_saves.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	add_child(_saves)
	_button(self, "Load selected world…", _confirm_restore)
	_button(self, "Overwrite selected save…", _confirm_overwrite)
	_overwrite_confirmation = ConfirmationDialog.new()
	_overwrite_confirmation.title = "Overwrite saved world?"
	_overwrite_confirmation.confirmed.connect(func() -> void:
		_send("save", "", HTTPClient.METHOD_POST, {"overwrite_id": _overwrite_id, "include_archive": _overwrite_archive}))
	add_child(_overwrite_confirmation)
	var help := Label.new()
	help.text = "Pause before saving or loading. Loading replaces unsaved progress and leaves the world paused. Saves include citizens, resources, buildings and the clock; they are not full history replays."
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(help)
	_confirmation = ConfirmationDialog.new()
	_confirmation.title = "Replace active world?"
	_confirmation.confirmed.connect(func() -> void: _send("restore", "/" + _restore_id + "/restore", HTTPClient.METHOD_POST))
	add_child(_confirmation)
	_request = HTTPRequest.new()
	_request.timeout = 35.0
	add_child(_request)
	_request.request_completed.connect(_completed)
	_watchdog = Timer.new()
	_watchdog.one_shot = true
	_watchdog.wait_time = 38.0
	_watchdog.timeout.connect(_cancel_request.bind(true))
	add_child(_watchdog)
	_token.text_changed.connect(func(_text: String) -> void:
		_connection.text = "SUPABASE · NOT CHECKED"
		_connection.add_theme_color_override("font_color", Color("a8bec0"))
		_status.text = "Credentials changed · connection not checked."
		_saves.clear())

func _button(parent: Node, title: String, callback: Callable) -> void:
	var button := Button.new()
	button.text = title
	button.pressed.connect(callback)
	parent.add_child(button)
	_buttons.append(button)

func _busy(value: bool) -> void:
	for button: Button in _buttons:
		button.disabled = value
	_token.editable = not value
	_archive.disabled = value
	_saves.disabled = value
	_cancel.disabled = not value

func _cancel_request(timed_out := false) -> void:
	if _operation.is_empty():
		return
	var was_save := _operation == "save"
	_request.cancel_request()
	_watchdog.stop()
	_operation = ""
	_busy(false)
	_connection.text = "SUPABASE · NOT VERIFIED"
	_connection.add_theme_color_override("font_color", Color("ef826f"))
	_status.text = "Request timed out. Check that the backend is running." if timed_out else "Request cancelled."
	if was_save:
		_status.text += " The server may still finish saving; refresh saves before retrying."

func _confirm_restore() -> void:
	if _saves.selected < 0 or _saves.item_count == 0:
		_status.text = "Refresh saves and select a saved world first."
		return
	_restore_id = str(_saves.get_item_metadata(_saves.selected))
	_confirmation.dialog_text = "Load %s? Unsaved progress will be replaced. Pause the simulation first." % _saves.get_item_text(_saves.selected)
	_confirmation.popup_centered(Vector2i(480, 180))

func _confirm_overwrite() -> void:
	if _saves.selected < 0 or _saves.item_count == 0:
		_status.text = "Refresh saves and select a saved world to overwrite."
		return
	_overwrite_id = str(_saves.get_item_metadata(_saves.selected))
	_overwrite_archive = _archive.button_pressed
	_overwrite_confirmation.dialog_text = "Replace %s with the current world? The previous world snapshot will be lost. The save name stays the same. Pause first. Research archive: %s." % [_saves.get_item_text(_saves.selected), "included" if _overwrite_archive else "not included"]
	_overwrite_confirmation.popup_centered(Vector2i(520, 200))

func _send(operation: String, path: String, method := HTTPClient.METHOD_GET, payload: Dictionary = {}) -> void:
	if not _operation.is_empty():
		return
	if _token.text.strip_edges().is_empty():
		_status.text = "Authentication needed: enter the backend admin token."
		return
	_operation = operation
	_busy(true)
	_connection.text = "SUPABASE · CHECKING…"
	_connection.add_theme_color_override("font_color", Color("dfc77d"))
	_status.text = "Contacting backend / Supabase…"
	_watchdog.start()
	var headers := PackedStringArray(["Content-Type: application/json", "X-Admin-Token: " + _token.text.strip_edges()])
	var error := _request.request(RuntimeConfig.http_url("/api/v1/checkpoints") + path, headers, method, JSON.stringify(payload) if method != HTTPClient.METHOD_GET else "")
	if error != OK:
		_watchdog.stop()
		_connection.text = "SUPABASE · NOT VERIFIED"
		_operation = ""
		_busy(false)
		_status.text = "Could not start request. Check the backend address."

func _completed(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_watchdog.stop()
	var operation := _operation
	_operation = ""
	_busy(false)
	if result != HTTPRequest.RESULT_SUCCESS:
		_connection.text = "SUPABASE · UNKNOWN — backend unreachable"
		_connection.add_theme_color_override("font_color", Color("ef826f"))
		_status.text = "Connection unavailable or timed out. No success was confirmed."
		return
	var data: Variant = JSON.parse_string(body.get_string_from_utf8())
	if code < 200 or code >= 300:
		_connection.text = "SUPABASE · CHECK FAILED — " + Time.get_time_string_from_system()
		_connection.add_theme_color_override("font_color", Color("ef826f"))
		var messages := {401: "Authentication required: check the backend admin token.", 503: "Supabase is not configured on the backend.", 502: "Supabase unavailable: check credentials, network and checkpoint migration.", 409: "Pause the simulation before saving/loading; check that a world exists."}
		if code == 401:
			_connection.text = "BACKEND · ADMIN TOKEN REJECTED — Supabase not checked"
		elif code == 409:
			_connection.text = "WORLD ACTION BLOCKED — Supabase not checked"
		_status.text = messages.get(code, "Request failed (HTTP %d). No success was confirmed." % code)
		if code in [502, 503] and data is Dictionary:
			_status.text = str(data.get("detail", _status.text))
		return
	var valid := data is Array if operation == "list" else data is Dictionary
	if valid and operation == "status":
		valid = data.get("connected", false) == true
	if valid and operation == "save":
		valid = data.has("id")
	if valid and operation == "restore":
		valid = data.get("state", "") == "PAUSED"
	if not valid:
		_connection.text = "SUPABASE · NOT VERIFIED"
		_status.text = "Unexpected response from backend. No success was confirmed."
		return
	_connection.text = "SUPABASE · CONNECTED — checked " + Time.get_time_string_from_system()
	_connection.add_theme_color_override("font_color", Color("72d6bb"))
	match operation:
		"status":
			_status.text = "CONNECTED · checkpoint table read verified just now. Writes are verified when you save."
		"save":
			if data.get("archive_saved", false):
				_status.text = "COMPLETE SAVE · world + %d events, %d metrics and %d experiments stored together. Refresh saves to load the world." % [int(data.get("events", 0)), int(data.get("metrics", 0)), int(data.get("experiments", 0))]
			else:
				_status.text = "SAVED · world snapshot only (includes citizens, animals and memories). Research history was not archived."
			if data.get("overwritten", false):
				_status.text = "OVERWRITTEN · selected save updated. " + _status.text
		"list":
			_saves.clear()
			if data is Array:
				for record: Variant in data:
					if record is Dictionary and record.has("id"):
						_saves.add_item("%s · tick %s · %s" % [record.get("label", "World"), record.get("tick", 0), record.get("created_at", "")])
						_saves.set_item_metadata(_saves.item_count - 1, record["id"])
			_status.text = "CONNECTED · %d saved worlds loaded (latest 50)." % _saves.item_count
		"restore":
			_status.text = "RESTORED · reloading world view. Simulation remains paused."
			world_restored.emit()
