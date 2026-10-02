extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var controls := preload("res://scripts/ui/CheckpointControls.gd").new()
	root.add_child(controls)
	controls._send("status", "/status")
	assert(controls._status.text.contains("Authentication needed"))
	assert(controls._token.secret)
	assert(controls._archive.button_pressed)
	controls._operation = "save"
	controls._completed(HTTPRequest.RESULT_SUCCESS, 201, PackedStringArray(), '{"id":"test","archive_saved":true,"events":3,"metrics":2,"experiments":0}'.to_utf8_buffer())
	assert(controls._status.text.contains("COMPLETE SAVE"))
	assert(controls._status.text.contains("3 events"))
	controls._operation = "status"
	controls._completed(HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray(), '{"connected":true}'.to_utf8_buffer())
	assert(controls._status.text.begins_with("CONNECTED"))
	controls._operation = "list"
	controls._completed(HTTPRequest.RESULT_SUCCESS, 200, PackedStringArray(), '[{"id":"example","label":"Winter","tick":42}]'.to_utf8_buffer())
	assert(controls._saves.item_count == 1)
	assert(controls._saves.get_item_metadata(0) == "example")
	controls._confirm_overwrite()
	assert(controls._overwrite_id == "example")
	assert(controls._overwrite_confirmation.dialog_text.contains("previous world snapshot will be lost"))
	controls._overwrite_confirmation.hide()
	controls._completed(HTTPRequest.RESULT_SUCCESS, 401, PackedStringArray(), '{}'.to_utf8_buffer())
	assert(controls._status.text.contains("Authentication required"))
	assert(controls._connection.text.contains("ADMIN TOKEN REJECTED"))
	controls._operation = "status"
	controls._completed(HTTPRequest.RESULT_SUCCESS, 503, PackedStringArray(), '{"detail":"SUPABASE_SECRET_KEY contains a public/anon key."}'.to_utf8_buffer())
	assert(controls._status.text.contains("public/anon"))
	controls._operation = "save"
	controls._busy(true)
	controls._cancel_request(true)
	assert(controls._operation.is_empty())
	assert(not controls._buttons[0].disabled)
	assert(controls._status.text.contains("may still finish"))
	controls._completed(HTTPRequest.RESULT_CANT_CONNECT, 0, PackedStringArray(), PackedByteArray())
	assert(controls._status.text.contains("unavailable"))
	print("PASS: checkpoint controls authentication, status, saved-world list and network errors")
	quit()
