# ActionsApiClient.gd
extends Node
class_name ActionsApiClient

## Reads backend-owned crafting and construction capabilities.

signal blueprints_received(blueprints: Dictionary)
signal request_failed(error_message: String)

@export var actions_url: String = ""

var _request: HTTPRequest


func _ready() -> void:
	if actions_url.is_empty():
		actions_url = RuntimeConfig.http_url("/api/v1/actions")
	_request = HTTPRequest.new()
	add_child(_request)
	_request.request_completed.connect(_on_request_completed)
	fetch_blueprints()


func fetch_blueprints() -> void:
	if _request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		return
	var error: int = _request.request(actions_url + "/blueprints")
	if error != OK:
		request_failed.emit("Could not request blueprints (error %d)." % error)


func _on_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		request_failed.emit("Blueprint request failed (HTTP %d)." % response_code)
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		request_failed.emit("Blueprint API returned invalid JSON.")
		return
	blueprints_received.emit(parsed as Dictionary)
