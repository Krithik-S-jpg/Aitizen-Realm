# Main.gd
extends Node2D

## Central orchestration core for the Aitizen Realm client.
## Connects networking, data parsing, rendering, and UI inspectors together.

@onready var api_client: WorldApiClient = $WorldApiClient
@onready var loader: WorldLoader = $WorldLoader
@onready var world_scene: Node2D = $World
@onready var hud: DebugHUD = $UI/DebugPanel
@onready var inspector: TileInspector = $UI/TileInspector

var _parsed_world: Dictionary = {}

func _ready() -> void:
	# Wire up connection and parsing signals
	api_client.world_data_received.connect(_on_world_data_received)
	api_client.connection_failed.connect(_on_connection_failed)

	loader.world_loaded.connect(_on_world_loaded)
	loader.validation_failed.connect(_on_validation_failed)

	hud.reload_requested.connect(_on_reload_requested)

	# Initial request on start
	_on_reload_requested()

func _unhandled_input(event: InputEvent) -> void:
	# Click to inspect tiles
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var global_mouse_pos = get_global_mouse_position()
		var map_pos = world_scene.renderer.local_to_map(world_scene.renderer.to_local(global_mouse_pos))

		if _parsed_world.has("tiles") and _parsed_world["tiles"].has(map_pos):
			var tile_data = _parsed_world["tiles"][map_pos]
			inspector.display_tile_info(tile_data, _parsed_world["chunk_size"])

func _on_world_data_received(data: Dictionary) -> void:
	loader.load_world_from_json(data)

func _on_world_loaded(parsed_world: Dictionary) -> void:
	_parsed_world = parsed_world

	# Explicitly print metrics as requested by the original specs
	print("World width: %d" % _parsed_world["width"])
	print("World height: %d" % _parsed_world["height"])
	print("Chunk size: %d" % _parsed_world["chunk_size"])
	print("Number of tiles: %d" % _parsed_world["tiles"].size())

	# Instruct visual renderer to draw
	world_scene.render_parsed_world(_parsed_world)

	# Update debug labels
	hud.update_status(true)
	hud.update_world_info(
		api_client.backend_url,
		_parsed_world["width"],
		_parsed_world["height"],
		_parsed_world["chunk_size"],
		_parsed_world["tiles"].size()
	)

func _on_connection_failed(error_message: String) -> void:
	hud.update_status(false, error_message)

func _on_validation_failed(error_message: String) -> void:
	hud.update_status(false, "Schema Validation Error: " + error_message)

func _on_reload_requested() -> void:
	hud.update_status(true) # clears disconnect labels
	api_client.fetch_world()
