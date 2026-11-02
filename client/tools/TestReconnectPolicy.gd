extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var client := WorldApiClient.new()
	root.add_child(client)
	client._handle_failure("offline")
	assert(not client._reconnect_timer.is_stopped())
	assert(client._reconnect_delay == 4.0)
	client._reconnect_timer.stop()
	client._handle_failure("offline again")
	assert(client._reconnect_delay == 8.0)
	client._reconnect_timer.stop()
	client._request_kind = "world"
	client._on_request_completed(HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray(), "{}".to_utf8_buffer())
	assert(client._reconnect_delay == 2.0)
	assert(client._reconnect_timer.is_stopped())
	client.queue_free()
	print("Reconnect policy passed")
	quit()
