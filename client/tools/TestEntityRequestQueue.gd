extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var client := EntityApiClient.new()
	root.add_child(client)
	var errors: Array[String] = []
	client.request_failed.connect(func(message: String) -> void: errors.append(message))
	client._busy = true
	for index in range(20):
		client.fetch_overview()
	assert(client._pending.size() == 1)
	assert(errors.is_empty())
	client.set_ai_mode("first", "utility")
	client.fetch_overview()
	assert(client._pending.size() == 2)
	assert(client._pending[0].operation == "dive")
	assert(client._pending[1].operation == "overview")
	# A completion listener's refresh must be queued, not rejected or nested.
	client.dive_started.connect(client.fetch_overview)
	client._operation = "dive"
	client._on_request_completed(HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray(), "{}".to_utf8_buffer())
	assert(not client._busy)
	assert(client._pending.size() == 2)
	assert(errors.is_empty())
	client._busy = true
	client._on_request_completed(HTTPRequest.RESULT_TIMEOUT, 0, PackedStringArray(), PackedByteArray())
	assert(not client._busy)
	assert(errors.size() == 1)
	assert(client._request.timeout == 20.0)
	client._pending.clear()
	client.queue_free()
	print("PASS: refresh coalescing, retained commands, reentrant refresh and timeout recovery")
	quit()
