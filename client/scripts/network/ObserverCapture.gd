extends Node
## Captures only the game viewport, and only while the local connector has a lease.
var _request: HTTPRequest
var _upload: HTTPRequest

func _ready() -> void:
	_request = HTTPRequest.new()
	_request.timeout = 5
	add_child(_request)
	_upload = HTTPRequest.new()
	_upload.timeout = 8
	add_child(_upload)
	_request.request_completed.connect(_status)
	var timer := Timer.new()
	timer.wait_time = 45
	timer.autostart = true
	timer.timeout.connect(func(): _request.request(RuntimeConfig.http_url("/api/v1/observer/capture-status")))
	add_child(timer)

func _status(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		return
	var state: Variant = JSON.parse_string(body.get_string_from_utf8())
	if not state is Dictionary or not state.get("enabled", false):
		return
	await RenderingServer.frame_post_draw
	var picture := get_viewport().get_texture().get_image()
	if picture.get_width() > 1280:
		picture.resize(1280, roundi(picture.get_height() * 1280.0 / picture.get_width()))
	_upload.request_raw(RuntimeConfig.http_url("/api/v1/observer/picture"), PackedStringArray(["Content-Type: image/jpeg"]), HTTPClient.METHOD_POST, picture.save_jpg_to_buffer(.7))
