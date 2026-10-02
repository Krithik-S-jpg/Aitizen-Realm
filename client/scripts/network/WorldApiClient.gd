# WorldApiClient.gd
extends Node
class_name WorldApiClient

## Connects to the FastAPI backend to fetch map data, managing timeouts and retries.

signal world_data_received(data: Dictionary)
signal chunk_data_received(data: Dictionary)
signal resources_data_received(resources: Array)
signal structures_data_received(structures: Array)
signal connection_failed(error_message: String)

@export var backend_url: String = ""
@export var request_timeout: float = 5.0
@export var max_retries: int = 3

var _retry_count: int = 0
var _http_request: HTTPRequest
var _is_generating: bool = false
var _request_in_flight: bool = false
var _request_kind: String = "world"
var _chunk_queue: Array[Vector2i] = []
var _requested_chunks: Dictionary = {}
var _active_chunk := Vector2i.ZERO
var _generation_options: Dictionary = {}

func _ready() -> void:
	if backend_url.is_empty():
		backend_url = RuntimeConfig.http_url("/api/v1/world")
	_http_request = HTTPRequest.new()
	add_child(_http_request)
	_http_request.request_completed.connect(_on_request_completed)
	_http_request.timeout = request_timeout

## Initiates a GET request to the specified backend URL.
func fetch_world() -> void:
	if _request_in_flight:
		return
	_is_generating = false
	_request_kind = "world"
	_chunk_queue.clear()
	_requested_chunks.clear()
	var err = _http_request.request(backend_url)
	if err != OK:
		_handle_failure("Failed to initiate request (Error code %d)" % err)
	else:
		_request_in_flight = true


## Requests a completely new backend-owned world. Generation is deterministic
## when a seed is supplied; omitting it asks the backend for a secure random seed.
func generate_new_world(options: Dictionary = {}) -> void:
	if _request_in_flight:
		return
	_generation_options = sanitize_generation_options(options)
	_is_generating = true
	_request_kind = "generate"
	_chunk_queue.clear()
	_requested_chunks.clear()
	var err = _http_request.request(
		generation_url(backend_url, _generation_options),
		PackedStringArray(),
		HTTPClient.METHOD_POST
	)
	if err != OK:
		_handle_failure("Failed to request a new world (Error code %d)" % err)
	else:
		_request_in_flight = true


static func sanitize_generation_options(options: Dictionary) -> Dictionary:
	var sanitized := {
		"width": clampi(int(options.get("width", 64)), 8, 128),
		"height": clampi(int(options.get("height", 64)), 8, 128),
	}
	if options.has("seed") and options["seed"] != null:
		sanitized["seed"] = clampi(int(options["seed"]), 0, 2147483647)
	var avatar_id := str(options.get("avatar_id", "scout"))
	if avatar_id in ["scout", "builder", "herbalist", "scholar", "cook", "miner", "fisher", "artisan"]:
		sanitized["avatar_id"] = avatar_id
	return sanitized


static func generation_url(base_url: String, options: Dictionary) -> String:
	var safe := sanitize_generation_options(options)
	var url := "%s/generate?width=%d&height=%d" % [base_url, safe.width, safe.height]
	if safe.has("seed"):
		url += "&seed=%d" % int(safe.seed)
	url += "&player_avatar=%s" % str(safe.get("avatar_id", "scout"))
	return url


func request_chunk(chunk_position: Vector2i) -> void:
	if _requested_chunks.has(chunk_position):
		return
	_requested_chunks[chunk_position] = true
	_chunk_queue.append(chunk_position)
	_pump_chunk_queue()


func fetch_resources() -> void:
	if _request_in_flight:
		return
	_request_kind = "resources"
	var err := _http_request.request(backend_url + "/live")
	if err != OK:
		_handle_failure("Failed to refresh live resources (Error %d)" % err)
		return
	_request_in_flight = true


func mark_chunk_loaded(chunk_position: Vector2i) -> void:
	_requested_chunks[chunk_position] = true


func _pump_chunk_queue() -> void:
	if _request_in_flight or _chunk_queue.is_empty():
		return
	_active_chunk = _chunk_queue.pop_front()
	_request_kind = "chunk"
	var url := "%s/chunk?chunk_x=%d&chunk_y=%d" % [
		backend_url, _active_chunk.x, _active_chunk.y
	]
	var err := _http_request.request(url)
	if err != OK:
		_requested_chunks.erase(_active_chunk)
		_handle_failure("Failed to request chunk %s (Error %d)" % [_active_chunk, err])
		return
	_request_in_flight = true

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_request_in_flight = false
	if result != HTTPRequest.RESULT_SUCCESS:
		if _request_kind == "chunk":
			_requested_chunks.erase(_active_chunk)
			_handle_failure("Chunk request failed.")
			_pump_chunk_queue()
			return
		if _retry_count < max_retries:
			_retry_count += 1
			print("Request failed. Retrying... (%d/%d)" % [_retry_count, max_retries])
			if _is_generating:
				generate_new_world(_generation_options)
			else:
				fetch_world()
		else:
			_handle_failure("Request timed out or network is unavailable after %d retries." % max_retries)
		return

	if response_code != 200:
		_handle_failure("Server responded with HTTP code %d" % response_code)
		return

	var json = JSON.new()
	var err = json.parse(body.get_string_from_utf8())
	if err != OK:
		_handle_failure("Failed to parse JSON response.")
		return

	var data = json.get_data()
	if _request_kind == "resources":
		if not data is Dictionary or not data.get("resources") is Array or not data.get("structures") is Array:
			_handle_failure("Live scene payload is invalid.")
			return
		_retry_count = 0
		resources_data_received.emit(data["resources"])
		structures_data_received.emit(data["structures"])
		_pump_chunk_queue()
		return
	if typeof(data) != TYPE_DICTIONARY:
		_handle_failure("JSON payload is not a valid dictionary.")
		return

	_retry_count = 0
	_is_generating = false
	if _request_kind == "chunk":
		chunk_data_received.emit(data)
		_pump_chunk_queue()
	else:
		world_data_received.emit(data)
		_pump_chunk_queue()

func _handle_failure(error_msg: String) -> void:
	_retry_count = 0
	connection_failed.emit(error_msg)
