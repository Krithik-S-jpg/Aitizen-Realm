extends SceneTree

var received := false
var disconnected := false
var api: WorldApiClient
var marker := ""

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	print("Reconnect test started")
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2)
	marker = args[1]
	api = WorldApiClient.new()
	api.backend_url = args[0] + "/api/v1/world"
	api.request_timeout = 1
	api.max_retries = 0
	root.add_child(api)
	api.connection_failed.connect(func(message: String) -> void:
		print("Observed disconnect: " + message)
		disconnected = true)
	api.world_data_received.connect(func(data: Dictionary) -> void:
		if not data.has("width"):
			quit(2)
			return
		if not received:
			received = true
			var file := FileAccess.open(marker, FileAccess.WRITE)
			file.store_string("ready")
			file.close()
		elif disconnected:
			print("PASS: actual Godot HTTP client reconnected after backend restart")
			quit())
	api.fetch_world()
	# Trigger a read while the test server is down; subsequent retries belong to
	# WorldApiClient, not to the test loop.
	while not received:
		await create_timer(.1).timeout
	await create_timer(2).timeout
	api.fetch_world()
	await create_timer(35).timeout
	quit(3)
