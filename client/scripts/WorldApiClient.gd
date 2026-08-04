# WorldApiClient.gd
extends Node
class_name WorldApiClient

## Handles HTTP communication with the Aitizen Realm backend to fetch world state data.

signal world_data_received(data: Dictionary)
signal connection_failed(error_message: String)

@export var backend_url: String = "http://127.0.0.1:8000/api/v1/world"

@onready var http_request: HTTPRequest = HTTPRequest.new()

func _ready() -> void:
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)

## Initiates a network request to the backend.
func fetch_world() -> void:
	var err = http_request.request(backend_url)
	if err != OK:
		connection_failed.emit("Failed to initiate HTTP request (Error code: %d)" % err)

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		connection_failed.emit("Network request failed. Is backend online?")
		return
	if response_code != 200:
		connection_failed.emit("Backend responded with HTTP status %d" % response_code)
		return

	var json = JSON.new()
	var err = json.parse(body.get_string_from_utf8())
	if err != OK:
		connection_failed.emit("Failed to parse JSON response.")
		return

	var data = json.get_data()
	if typeof(data) != TYPE_DICTIONARY:
		connection_failed.emit("JSON payload is not a valid dictionary.")
		return

	world_data_received.emit(data)
