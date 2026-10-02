extends Node
class_name ResearchApiClient

## Read-only client for backend-owned experiment metrics and history export.

signal observation_received(data: Dictionary)
signal world_events_received(events: Array)
signal request_failed(message: String)

@export var export_url := ""
var _request: HTTPRequest
var _events_request: HTTPRequest
var _events_url := ""


func _ready() -> void:
	if export_url.is_empty():
		export_url = RuntimeConfig.http_url("/api/v1/research/export")
	_events_url = RuntimeConfig.http_url("/api/v1/research/events")
	_request = HTTPRequest.new()
	add_child(_request)
	_request.request_completed.connect(_on_completed)
	_events_request = HTTPRequest.new()
	add_child(_events_request)
	_events_request.request_completed.connect(_on_events_completed)


func fetch_observation() -> void:
	if _request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	var error := _request.request(export_url)
	if error != OK:
		request_failed.emit("Could not request research data (error %d)." % error)


func fetch_events(after_sequence: int) -> void:
	if _events_request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	var error := _events_request.request("%s?after_sequence=%d&limit=100" % [_events_url, after_sequence])
	if error != OK:
		request_failed.emit("Could not request world events (error %d)." % error)


func _on_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		request_failed.emit("Research request failed (HTTP %d)." % response_code)
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		request_failed.emit("Research response was not a JSON object.")
		return
	observation_received.emit(parsed as Dictionary)


func _on_events_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		request_failed.emit("World-event request failed (HTTP %d)." % response_code)
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if parsed is Array:
		world_events_received.emit(parsed as Array)
	else:
		request_failed.emit("World-event response was not a JSON array.")
