extends Node
class_name ResearchApiClient

## Read-only client for backend-owned experiment metrics and history export.

signal observation_received(data: Dictionary)
signal request_failed(message: String)

@export var export_url := ""
var _request: HTTPRequest


func _ready() -> void:
	if export_url.is_empty():
		export_url = RuntimeConfig.http_url("/api/v1/research/export")
	_request = HTTPRequest.new()
	add_child(_request)
	_request.request_completed.connect(_on_completed)


func fetch_observation() -> void:
	if _request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	var error := _request.request(export_url)
	if error != OK:
		request_failed.emit("Could not request research data (error %d)." % error)


func _on_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		request_failed.emit("Research request failed (HTTP %d)." % response_code)
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		request_failed.emit("Research response was not a JSON object.")
		return
	observation_received.emit(parsed as Dictionary)
