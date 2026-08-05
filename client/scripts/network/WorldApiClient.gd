# WorldApiClient.gd
extends Node
class_name WorldApiClient

## Connects to the FastAPI backend to fetch map data, managing timeouts and retries.

signal world_data_received(data: Dictionary)
signal connection_failed(error_message: String)

@export var backend_url: String = "http://127.0.0.1:8000/api/v1/world"
@export var request_timeout: float = 5.0
@export var max_retries: int = 3

var _retry_count: int = 0
var _http_request: HTTPRequest

func _ready() -> void:
	_http_request = HTTPRequest.new()
	add_child(_http_request)
	_http_request.request_completed.connect(_on_request_completed)
	_http_request.timeout = request_timeout

## Initiates a GET request to the specified backend URL.
func fetch_world() -> void:
	var err = _http_request.request(backend_url)
	if err != OK:
		_handle_failure("Failed to initiate request (Error code %d)" % err)

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		if _retry_count < max_retries:
			_retry_count += 1
			print("Request failed. Retrying... (%d/%d)" % [_retry_count, max_retries])
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
	if typeof(data) != TYPE_DICTIONARY:
		_handle_failure("JSON payload is not a valid dictionary.")
		return

	_retry_count = 0
	world_data_received.emit(data)

func _handle_failure(error_msg: String) -> void:
	_retry_count = 0
	connection_failed.emit(error_msg)
