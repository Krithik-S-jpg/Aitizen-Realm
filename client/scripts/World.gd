# World.gd
extends Node2D

## Main scene orchestrator connecting HTTP requests, loader models, tile renderers, and UI layers.

@onready var api_client: WorldApiClient = $WorldApiClient
@onready var loader: WorldLoader = $WorldLoader
@onready var renderer: WorldRenderer = $TileMapLayer
@onready var hud: HUD = $CanvasLayer/HUD
@onready var inspector: TileInspector = $CanvasLayer/Inspector

var _parsed_world: Dictionary = {}

func _ready() -> void:
	api_client.world_data_received.connect(_on_world_data_received)
	api_client.connection_failed.connect(_on_connection_failed)
	hud.reload_requested.connect(_on_reload_requested)

	# Initial fetch
	_on_reload_requested()

func _unhandled_input(event: InputEvent) -> void:
	# Click to inspect tiles
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var global_mouse_pos = get_global_mouse_position()
		var map_pos = renderer.local_to_map(renderer.to_local(global_mouse_pos))

		if _parsed_world.has("tiles") and _parsed_world["tiles"].has(map_pos):
			var tile_data = _parsed_world["tiles"][map_pos]
			inspector.display_tile_info(tile_data, _parsed_world["chunk_size"])

func _on_world_data_received(data: Dictionary) -> void:
	_parsed_world = loader.parse_world_data(data)
	if _parsed_world.is_empty():
		_on_connection_failed("Malformed data structure returned by backend")
		return

	# Draw the world
	renderer.render_world(_parsed_world["tiles"])

	# Update HUD metrics
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

func _on_reload_requested() -> void:
	hud.update_status(true) # clear disconnect UI during load attempts
	api_client.fetch_world()
