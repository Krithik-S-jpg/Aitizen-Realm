extends AcceptDialog

var owner_id := ""
var log_view: RichTextLabel
var input: LineEdit
var send: Button
var request: HTTPRequest

func _ready() -> void:
	title = "Talk to citizen · dialogue does not issue commands"
	var layout := VBoxContainer.new()
	add_child(layout)
	log_view = RichTextLabel.new()
	log_view.custom_minimum_size = Vector2(500, 260)
	log_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_view.scroll_following = true
	layout.add_child(log_view)
	input = LineEdit.new()
	input.max_length = 1000
	input.placeholder_text = "Ask about needs, work or plans…"
	layout.add_child(input)
	send = Button.new()
	send.text = "Send"
	layout.add_child(send)
	request = HTTPRequest.new()
	request.timeout = 30
	add_child(request)
	send.pressed.connect(_send)
	input.text_submitted.connect(func(_text: String) -> void: _send())
	request.request_completed.connect(_received)

func open_citizen(citizen: Dictionary) -> void:
	if send.disabled:
		popup_centered(Vector2i(580, 420))
		return
	owner_id = str(citizen.get("id", ""))
	log_view.text = "Talking with %s\n\n" % citizen.get("name", "Citizen")
	for entry: Dictionary in citizen.get("metadata", {}).get("player_chat", []):
		log_view.text += "%s: %s\n\n" % [entry.get("role", ""), entry.get("content", "")]
	popup_centered(Vector2i(580, 420))

func _send() -> void:
	if send.disabled or input.text.strip_edges().is_empty():
		return
	var message := input.text.strip_edges()
	var error := request.request(RuntimeConfig.http_url("/api/v1/entities/%s/chat" % owner_id), PackedStringArray(["Content-Type: application/json"]), HTTPClient.METHOD_POST, JSON.stringify({"message": message}))
	if error != OK:
		log_view.text += "Could not send. Please retry.\n"
		return
	log_view.text += "You: %s\n\n" % message
	input.clear()
	send.disabled = true
	send.text = "Thinking…"

func _received(result: int, code: int, _headers: PackedStringArray, bytes: PackedByteArray) -> void:
	send.disabled = false
	send.text = "Send"
	var data: Variant = JSON.parse_string(bytes.get_string_from_utf8())
	if result == HTTPRequest.RESULT_SUCCESS and code == 200 and data is Dictionary:
		log_view.text += "Citizen: %s\n[%s]\n\n" % [data.get("reply", ""), data.get("source", "")]
	else:
		log_view.text += "Message failed (HTTP %d). Please retry.\n" % code
