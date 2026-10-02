# SimulationApiClient.gd
extends Node
class_name SimulationApiClient

## Controls and observes the backend-authoritative simulation engine.

signal state_received(state: Dictionary)
signal simulation_event_received(event: Dictionary)
signal connection_changed(is_connected: bool)
signal request_failed(error_message: String)
signal environment_received(data: Dictionary)

@export var simulation_url: String = ""
@export var websocket_url: String = ""

var _request: HTTPRequest
var _socket := WebSocketPeer.new()
var _socket_was_open := false
var _request_in_flight := false
var _requested_path := ""
var _pending_path := ""
var _pending_method := HTTPClient.METHOD_GET
var _pending_body := ""


func _ready() -> void:
	if simulation_url.is_empty():
		simulation_url = RuntimeConfig.http_url("/api/v1/simulation")
	if websocket_url.is_empty():
		websocket_url = RuntimeConfig.websocket_url("/api/v1/simulation/ws")
	_request = HTTPRequest.new()
	add_child(_request)
	_request.request_completed.connect(_on_request_completed)
	connect_websocket()
	fetch_state()


func _process(_delta: float) -> void:
	_socket.poll()
	var socket_state := _socket.get_ready_state()
	if socket_state == WebSocketPeer.STATE_OPEN:
		if not _socket_was_open:
			_socket_was_open = true
			connection_changed.emit(true)
		while _socket.get_available_packet_count() > 0:
			_parse_message(_socket.get_packet().get_string_from_utf8())
	elif socket_state == WebSocketPeer.STATE_CLOSED and _socket_was_open:
		_socket_was_open = false
		connection_changed.emit(false)


func connect_websocket() -> void:
	if _socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		return
	var error := _socket.connect_to_url(websocket_url)
	if error != OK:
		request_failed.emit("Could not connect simulation WebSocket (error %d)." % error)


func fetch_state() -> void:
	_send_request("/state", HTTPClient.METHOD_GET)


func send_command(command: String) -> void:
	if command not in ["start", "pause", "resume", "step", "stop"]:
		request_failed.emit("Unknown simulation command: %s" % command)
		return
	_send_request("/" + command, HTTPClient.METHOD_POST)


func set_tick_rate(ticks_per_second: float) -> void:
	_send_request(
		"/rate?ticks_per_second=%s" % str(ticks_per_second),
		HTTPClient.METHOD_POST
	)


func fetch_environment() -> void:
	_send_request("/environment", HTTPClient.METHOD_GET)


func set_environment(settings: Dictionary) -> void:
	_send_request("/environment", HTTPClient.METHOD_POST, JSON.stringify(settings))


func reset_environment() -> void:
	_send_request("/environment", HTTPClient.METHOD_DELETE)


func _send_request(path: String, method: HTTPClient.Method, body: String = "") -> void:
	if _request_in_flight:
		# Keep the latest user command instead of surfacing a harmless race as an error.
		if method != HTTPClient.METHOD_GET:
			_pending_path = path
			_pending_method = method
			_pending_body = body
		return
	_requested_path = path
	var headers := PackedStringArray(["Content-Type: application/json"]) if not body.is_empty() else PackedStringArray()
	var error := _request.request(simulation_url + path, headers, method, body)
	if error != OK:
		request_failed.emit("Could not send simulation request (error %d)." % error)
		return
	_request_in_flight = true


func _on_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	_request_in_flight = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		request_failed.emit("Simulation API request failed (HTTP %d)." % response_code)
		return

	var completed_path := _requested_path
	var message := body.get_string_from_utf8()
	if completed_path == "/environment":
		var parsed: Variant = JSON.parse_string(message)
		if parsed is Dictionary:
			environment_received.emit(parsed as Dictionary)
		else:
			request_failed.emit("Environment API returned invalid JSON.")
	else:
		_parse_message(message)
	if not _pending_path.is_empty():
		var next_path := _pending_path
		var next_method := _pending_method
		var next_body := _pending_body
		_pending_path = ""
		_pending_body = ""
		call_deferred("_send_request", next_path, next_method, next_body)
	# Command responses do not include the complete clock state.
	elif completed_path != "/state" and completed_path != "/environment":
		call_deferred("fetch_state")


func _parse_message(message: String) -> void:
	var parsed = JSON.parse_string(message)
	if typeof(parsed) != TYPE_DICTIONARY:
		request_failed.emit("Simulation API returned invalid JSON.")
		return
	var data: Dictionary = parsed
	if data.get("type", "") == "event":
		simulation_event_received.emit(data)
	else:
		state_received.emit(data)
