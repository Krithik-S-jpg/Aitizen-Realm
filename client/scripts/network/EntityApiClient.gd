extends Node
class_name EntityApiClient

## Admin-facing client for authoritative entity lifecycle operations.

signal overview_received(entities: Array)
signal entity_created(entity: Dictionary)
signal entity_removed(entity: Dictionary)
signal observation_received(observation: Dictionary)
signal request_failed(error_message: String)

@export var entities_url := ""

var _request: HTTPRequest
var _operation := "overview"


func _ready() -> void:
	if entities_url.is_empty():
		entities_url = RuntimeConfig.http_url("/api/v1/entities")
	_request = HTTPRequest.new()
	add_child(_request)
	_request.request_completed.connect(_on_request_completed)


func fetch_overview() -> void:
	_send(entities_url + "/admin/overview", HTTPClient.METHOD_GET, "overview")


func create_agent(agent_name: String, x: int, y: int, radius: int, autonomous: bool) -> void:
	var tags: Array[String] = []
	if autonomous:
		tags.append("autonomous")
	var body := JSON.stringify({
		"kind": "AGENT",
		"name": agent_name,
		"x": x,
		"y": y,
		"perception_radius": radius,
		"tags": tags
	})
	_send(entities_url, HTTPClient.METHOD_POST, "create", body)


func remove_agent(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id, HTTPClient.METHOD_DELETE, "remove")


func fetch_observation(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id + "/observation", HTTPClient.METHOD_GET, "observation")


func _send(url: String, method: HTTPClient.Method, operation: String, body := "") -> void:
	if _request.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		request_failed.emit("Agent administration request is already running.")
		return
	_operation = operation
	var headers := PackedStringArray(["Content-Type: application/json"])
	var error := _request.request(url, headers, method, body)
	if error != OK:
		request_failed.emit("Could not send agent request (error %d)." % error)


func _on_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		var detail := body.get_string_from_utf8()
		request_failed.emit("Agent request failed (HTTP %d): %s" % [response_code, detail])
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if _operation == "overview" and typeof(parsed) == TYPE_ARRAY:
		overview_received.emit(parsed as Array)
	elif typeof(parsed) == TYPE_DICTIONARY:
		if _operation == "create":
			entity_created.emit(parsed as Dictionary)
		elif _operation == "observation":
			observation_received.emit(parsed as Dictionary)
		else:
			entity_removed.emit(parsed as Dictionary)
 
