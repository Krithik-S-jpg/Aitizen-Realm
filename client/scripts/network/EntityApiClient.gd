extends Node
class_name EntityApiClient

## Admin-facing client for authoritative entity lifecycle operations.

signal overview_received(entities: Array)
signal entity_created(entity: Dictionary)
signal entity_removed(entity: Dictionary)
signal observation_received(observation: Dictionary)
signal request_failed(error_message: String)
signal dive_started()

@export var entities_url := ""

var _request: HTTPRequest
var _operation := "overview"
var _busy := false
var _pending: Array[Dictionary] = []
const MAX_PENDING := 16


func _ready() -> void:
	if entities_url.is_empty():
		entities_url = RuntimeConfig.http_url("/api/v1/entities")
	_request = HTTPRequest.new()
	_request.timeout = 20.0
	add_child(_request)
	_request.request_completed.connect(_on_request_completed)


func fetch_overview() -> void:
	_send(entities_url + "/admin/overview", HTTPClient.METHOD_GET, "overview")

func start_dive(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id + "/dive", HTTPClient.METHOD_POST, "dive", "{}")

func return_from_dive(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id + "/dive/return", HTTPClient.METHOD_POST, "dive", "{}")

func operate_boat(entity_id: String, command: String, destination: Vector2i) -> void:
	_send(entities_url + "/" + entity_id + "/boat", HTTPClient.METHOD_POST, "dive", JSON.stringify({"command": command, "x": destination.x, "y": destination.y}))


func explore_cave(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id + "/cave", HTTPClient.METHOD_POST, "dive", "{}")

func set_ai_mode(entity_id: String, mode: String) -> void:
	_send(entities_url + "/" + entity_id + "/ai-mode", HTTPClient.METHOD_POST, "dive", JSON.stringify({"mode": mode}))

func give_supplies(entity_id: String, recipient: String, item: String, amount: float) -> void:
	_send(entities_url + "/" + entity_id + "/give", HTTPClient.METHOD_POST, "dive", JSON.stringify({"recipient_id": recipient, "item": item, "amount": amount}))

func create_agent(agent_name: String, x: int, y: int, radius: int, autonomous: bool, avatar_id: String, gender := "unspecified", diet := "omnivore") -> void:
	var tags: Array[String] = []
	if autonomous:
		tags.append("autonomous")
	var body := JSON.stringify({
		"kind": "AGENT",
		"name": agent_name,
		"x": x,
		"y": y,
		"perception_radius": radius,
		"tags": tags,
		"avatar_id": avatar_id,
		"gender": gender,
		"diet": diet,
		"auto_spawn": true
	})
	_send(entities_url, HTTPClient.METHOD_POST, "create", body)


func remove_agent(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id, HTTPClient.METHOD_DELETE, "remove")


func fetch_observation(entity_id: String) -> void:
	_send(entities_url + "/" + entity_id + "/observation", HTTPClient.METHOD_GET, "observation")


func _send(url: String, method: HTTPClient.Method, operation: String, body := "") -> void:
	# Refreshes may arrive while a command completes or the panel reopens.
	# Keep one pending read per view; never replay a mutation automatically.
	if method == HTTPClient.METHOD_GET:
		for index in range(_pending.size() - 1, -1, -1):
			if _pending[index].method == HTTPClient.METHOD_GET and _pending[index].operation == operation:
				_pending.remove_at(index)
	if _pending.size() >= MAX_PENDING:
		request_failed.emit("Too many pending citizen commands. Please wait for them to finish.")
		return
	_pending.append({"url": url, "method": method, "operation": operation, "body": body})
	if not _busy:
		_drain.call_deferred()


func _drain() -> void:
	if _busy or _pending.is_empty():
		return
	var command: Dictionary = _pending.pop_front()
	_busy = true
	_operation = str(command.operation)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var error := _request.request(str(command.url), headers, int(command.method), str(command.body))
	if error != OK:
		request_failed.emit("Could not send agent request (error %d)." % error)
		_finish_request()


func _finish_request() -> void:
	_busy = false
	_drain.call_deferred()


func _on_request_completed(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray
) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		var detail := body.get_string_from_utf8()
		var error_decoder := JSON.new()
		var error_payload: Variant = error_decoder.data if not detail.is_empty() and error_decoder.parse(detail) == OK else null
		if error_payload is Dictionary and error_payload.get("detail") is String:
			detail = str(error_payload["detail"])
		if result == HTTPRequest.RESULT_TIMEOUT:
			request_failed.emit("Citizen request timed out. Refresh before repeating a command; completion was not confirmed.")
		else:
			request_failed.emit("Agent request failed (HTTP %d): %s" % [response_code, detail])
		_finish_request()
		return
	var decoder := JSON.new()
	var parsed: Variant = decoder.data if decoder.parse(body.get_string_from_utf8()) == OK else null
	if _operation == "overview" and typeof(parsed) == TYPE_ARRAY:
		overview_received.emit(parsed as Array)
	elif _operation != "overview" and typeof(parsed) == TYPE_DICTIONARY:
		if _operation == "dive":
			dive_started.emit()
		elif _operation == "create":
			entity_created.emit(parsed as Dictionary)
		elif _operation == "observation":
			observation_received.emit(parsed as Dictionary)
		else:
			entity_removed.emit(parsed as Dictionary)
	else:
		request_failed.emit("Agent request returned an unexpected response.")
	_finish_request()
 
