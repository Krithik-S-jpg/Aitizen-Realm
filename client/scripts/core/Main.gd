# Main.gd
extends Node2D

## Central orchestration core for the Aitizen Realm client.
## Connects networking, data parsing, rendering, and UI inspectors together.

@onready var api_client: WorldApiClient = $WorldApiClient
@onready var simulation_client: SimulationApiClient = $SimulationApiClient
@onready var actions_client: Node = $ActionsApiClient
@onready var loader: WorldLoader = $WorldLoader
@onready var world_scene: WorldView = $World
@onready var hud: DebugHUD = $UI/DebugPanel
@onready var inspector: TileInspector = $UI/TileInspector
@onready var camera: CameraController = $Camera2D
@onready var day_night_overlay: ColorRect = $UI/DayNightOverlay
@onready var crafting_panel: Control = $UI/CraftingPanel
@onready var admin_panel: AdminPanel = $UI/AdminPanel
@onready var entity_client: EntityApiClient = $EntityApiClient
@onready var minimap: WorldMinimap = $UI/WorldMinimap
@onready var analysis_panel: AnalysisPanel = $UI/AnalysisPanel
@onready var settings_panel: SimulationSettingsPanel = $UI/SimulationSettingsPanel
@onready var event_overlay: WorldEventOverlay = $UI/WorldEventOverlay
@onready var research_client: ResearchApiClient = $ResearchApiClient

var _parsed_world: Dictionary = {}
var _has_centered_camera := false
var _calendar_state: Dictionary = {}
var _loaded_chunks: Dictionary = {}
var _chunk_check_elapsed: float = 0.0
var _player_entity: Dictionary = {}
var _follow_player := true
var _tracked_entity_id := ""
var _tick_rate := 1.0
var _last_world_event_sequence := -1

func _ready() -> void:
	# Wire up connection and parsing signals
	api_client.world_data_received.connect(_on_world_data_received)
	api_client.connection_failed.connect(_on_connection_failed)

	loader.world_loaded.connect(_on_world_loaded)
	loader.chunk_loaded.connect(_on_chunk_loaded)
	api_client.chunk_data_received.connect(loader.merge_chunk_data)
	api_client.resources_data_received.connect(_on_live_resources_received)
	api_client.structures_data_received.connect(_on_live_structures_received)
	loader.validation_failed.connect(_on_validation_failed)

	hud.reload_requested.connect(_on_reload_requested)
	hud.new_world_requested.connect(_on_new_world_requested)
	hud.simulation_command_requested.connect(simulation_client.send_command)
	hud.tick_rate_requested.connect(simulation_client.set_tick_rate)
	hud.admin_requested.connect(_open_admin)
	hud.crafting_requested.connect(crafting_panel.toggle_panel)
	hud.observation_layer_requested.connect(world_scene.renderer.set_observation_layer)
	hud.navigation_requested.connect(_on_navigation_requested)
	simulation_client.state_received.connect(_on_simulation_state_received)
	simulation_client.simulation_event_received.connect(_on_simulation_event_received)
	simulation_client.request_failed.connect(_on_simulation_request_failed)
	simulation_client.environment_received.connect(_on_environment_received)
	settings_panel.apply_requested.connect(_on_settings_apply_requested)
	settings_panel.reset_requested.connect(_on_settings_reset_requested)
	settings_panel.new_world_requested.connect(_on_new_world_requested)
	settings_panel.pause_requested.connect(func() -> void: simulation_client.send_command("pause"))
	settings_panel.world_restored.connect(func() -> void:
		_on_reload_requested()
		simulation_client.fetch_state()
		simulation_client.fetch_environment()
		entity_client.fetch_overview())
	actions_client.connect(
		"blueprints_received", Callable(crafting_panel, "display_blueprints")
	)
	actions_client.connect("request_failed", Callable(crafting_panel, "display_error"))
	crafting_panel.connect(
		"refresh_requested", Callable(actions_client, "fetch_blueprints")
	)
	admin_panel.create_agent_requested.connect(entity_client.create_agent)
	admin_panel.remove_agent_requested.connect(entity_client.remove_agent)
	admin_panel.refresh_requested.connect(entity_client.fetch_overview)
	admin_panel.focus_requested.connect(_focus_camera_at)
	entity_client.overview_received.connect(admin_panel.display_agents)
	entity_client.overview_received.connect(_on_live_entities_received)
	entity_client.entity_created.connect(_on_agent_created)
	entity_client.entity_removed.connect(_on_agent_removed)
	entity_client.request_failed.connect(admin_panel.display_error)
	minimap.navigate_requested.connect(_focus_camera_at)
	analysis_panel.refresh_requested.connect(research_client.fetch_observation)
	analysis_panel.focus_requested.connect(_focus_camera_at)
	research_client.observation_received.connect(analysis_panel.display_observation)
	research_client.world_events_received.connect(_on_world_events_received)
	research_client.request_failed.connect(analysis_panel.display_error)
	event_overlay.navigate_requested.connect(_focus_camera_at)

	# Initial request on start
	_on_reload_requested()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_F:
			_follow_player = not _follow_player
			if not _follow_player:
				camera.clear_follow_target()
			hud.update_player(_player_entity, _follow_player)
		elif event.keycode in [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]:
			_follow_player = false
			camera.clear_follow_target()
			hud.update_player(_player_entity, _follow_player)
	# Click to inspect tiles
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var global_mouse_pos: Vector2 = get_global_mouse_position()
		var map_pos: Vector2i = world_scene.renderer.local_to_map(world_scene.renderer.to_local(global_mouse_pos))

		if _parsed_world.has("tiles") and _parsed_world["tiles"].has(map_pos):
			var tile_data = _parsed_world["tiles"][map_pos]
			world_scene.renderer.set_selected_tile(map_pos)
			var entity_data: Dictionary = world_scene.renderer.get_entity_at(map_pos)
			if not entity_data.is_empty():
				_tracked_entity_id = str(entity_data.get("id", ""))
				_player_entity = entity_data
				_follow_player = true
				hud.update_player(_player_entity, _follow_player)
				inspector.display_entity_info(entity_data, int(_parsed_world["chunk_size"]))
				return
			var structure_data: Dictionary = world_scene.renderer.get_structure_at(map_pos)
			if not structure_data.is_empty():
				inspector.display_structure_info(structure_data)
				return
			var resource_data: Dictionary = world_scene.renderer.get_resource_at(map_pos)
			if resource_data.is_empty():
				inspector.display_tile_info(tile_data, _parsed_world["chunk_size"])
			else:
				inspector.display_resource_info(resource_data, _parsed_world["chunk_size"])
	elif event is InputEventMouseMotion and _parsed_world.has("tiles"):
		var local_mouse: Vector2 = world_scene.renderer.to_local(get_global_mouse_position())
		world_scene.renderer.set_hovered_tile(world_scene.renderer.local_to_map(local_mouse))


func _process(delta: float) -> void:
	if _parsed_world.is_empty():
		return
	if _follow_player and not _player_entity.is_empty():
		var entity_id := str(_player_entity.get("id", ""))
		camera.set_follow_target(world_scene.renderer.get_entity_visual_local(entity_id))
	_chunk_check_elapsed += delta
	if _chunk_check_elapsed < 0.35:
		return
	_chunk_check_elapsed = 0.0
	_request_chunks_around_camera()
	minimap.update_camera(world_scene.renderer.local_to_map(camera.position))

func _on_world_data_received(data: Dictionary) -> void:
	loader.load_world_from_json(data)

func _on_world_loaded(parsed_world: Dictionary) -> void:
	_parsed_world = parsed_world
	_update_player_entity()
	_register_initial_chunks()

	# Explicitly print metrics as requested by the original specs
	print("World width: %d" % _parsed_world["width"])
	print("World height: %d" % _parsed_world["height"])
	print("Chunk size: %d" % _parsed_world["chunk_size"])
	print("World seed: %d" % _parsed_world["seed"])
	print("Number of tiles: %d" % _parsed_world["tiles"].size())
	print("Number of resources: %d" % _parsed_world["resources"].size())

	# Instruct visual renderer to draw
	world_scene.render_parsed_world(_parsed_world)
	minimap.update_world(_parsed_world)
	hud.configure_observation_layers(_parsed_world.get("layer_support", {}))
	if not _has_centered_camera:
		_focus_camera_on_world()
		_has_centered_camera = true
	if not _calendar_state.is_empty():
		world_scene.configure_weather(
			_calendar_state,
			int(_parsed_world["width"]),
			int(_parsed_world["height"])
		)
	if settings_panel.visible:
		settings_panel.display_world_created(_parsed_world)

	# Update debug labels
	hud.update_status(true)
	hud.update_world_info(
		api_client.backend_url,
		_parsed_world["width"],
		_parsed_world["height"],
		_parsed_world["chunk_size"],
		_parsed_world["seed"],
		_parsed_world["tiles"].size(),
		_parsed_world["resources"].size()
	)

func _on_connection_failed(error_message: String) -> void:
	hud.update_status(false, error_message)

func _on_validation_failed(error_message: String) -> void:
	hud.update_status(false, "Schema Validation Error: " + error_message)

func _on_reload_requested() -> void:
	hud.update_status(true) # clears disconnect labels
	api_client.fetch_world()


func _on_new_world_requested(options: Dictionary = {}) -> void:
	hud.update_status(true)
	inspector.hide_inspector()
	world_scene.renderer.clear_selection()
	_has_centered_camera = false
	_loaded_chunks.clear()
	api_client.generate_new_world(options)


func _on_simulation_state_received(state: Dictionary) -> void:
	var engine_state := str(state.get("state", "UNKNOWN"))
	world_scene.set_simulation_running(engine_state.to_upper() == "RUNNING")
	var tick := int(state.get("current_tick", state.get("tick", 0)))
	var tick_rate := float(state.get("tick_rate", 1.0))
	_tick_rate = tick_rate
	world_scene.renderer.set_simulation_tick_rate(tick_rate)
	hud.update_simulation(engine_state, tick, tick_rate)
	hud.update_system_health(state.get("world_health", {}))
	_apply_calendar(state.get("calendar", {}))


func _on_simulation_event_received(event: Dictionary) -> void:
	var tick := int(event.get("tick", 0))
	hud.update_tick(tick)
	hud.add_simulation_event(str(event.get("name", "event")), tick)
	_apply_calendar(event.get("calendar", {}))
	var event_name := str(event.get("name", ""))
	if event_name.begins_with("simulation:") or (
		event_name == "tick:completed" and tick % 10 == 0
	):
		simulation_client.fetch_state()
	if event_name == "tick:completed" and tick % 120 == 0:
		api_client.fetch_world()
	elif event_name == "tick:completed" and tick % 2 == 0:
		api_client.fetch_resources()
	if event_name == "tick:completed":
		entity_client.fetch_overview()
		if tick % 2 == 0:
			research_client.fetch_events(_last_world_event_sequence)


func _on_simulation_request_failed(error_message: String) -> void:
	push_warning(error_message)
	if settings_panel.visible:
		settings_panel.display_error(error_message)


func _on_navigation_requested(mode: String) -> void:
	# UIManager owns ordinary page navigation; this handler owns environment controls.
	if mode != "settings":
		settings_panel.close_panel()
	match mode:
		"settings":
			settings_panel.open_panel(_calendar_state, _tick_rate, _parsed_world)
			simulation_client.fetch_environment()
		"world":
			admin_panel.close_page()
			analysis_panel.close_panel()
			settings_panel.close_panel()


func _on_settings_apply_requested(settings: Dictionary, tick_rate: float, visual_quality: String) -> void:
	_tick_rate = tick_rate
	world_scene.set_visual_quality(visual_quality)
	simulation_client.set_tick_rate(tick_rate)
	simulation_client.set_environment(settings)


func _on_settings_reset_requested() -> void:
	simulation_client.reset_environment()
	simulation_client.fetch_environment()


func _on_environment_received(data: Dictionary) -> void:
	settings_panel.display_environment(data)
	_apply_calendar(data.get("calendar", {}))


func _on_world_events_received(events: Array) -> void:
	if events.is_empty():
		return
	event_overlay.display_events(events)
	for event_value: Variant in events:
		if event_value is Dictionary:
			_last_world_event_sequence = maxi(
				_last_world_event_sequence,
				int((event_value as Dictionary).get("sequence", -1))
			)


func _focus_camera_on_world() -> void:
	var center := Vector2i(
		floori(float(_parsed_world["width"]) / 2.0),
		floori(float(_parsed_world["height"]) / 2.0)
	)
	camera.clear_follow_target()
	camera.jump_to(world_scene.renderer.map_to_local(center))
	var chunk_size: int = int(_parsed_world["chunk_size"])
	world_scene.renderer.set_visible_chunk_center(Vector2i(
		floori(float(center.x) / chunk_size),
		floori(float(center.y) / chunk_size)
	))


func _focus_camera_at(map_position: Vector2i) -> void:
	_follow_player = false
	camera.clear_follow_target()
	camera.jump_to(world_scene.renderer.map_to_local(map_position))
	hud.update_player(_player_entity, _follow_player)


func _apply_calendar(calendar: Dictionary) -> void:
	if calendar.is_empty():
		return
	_calendar_state = calendar
	hud.update_calendar(calendar)
	if not _parsed_world.is_empty():
		world_scene.configure_weather(
			calendar,
			int(_parsed_world["width"]),
			int(_parsed_world["height"])
		)
	match str(calendar.get("phase", "DAY")):
		"NIGHT":
			day_night_overlay.color = Color(0.04, 0.08, 0.22, 0.48)
		"DAWN":
			day_night_overlay.color = Color(1.0, 0.55, 0.28, 0.14)
		"DUSK":
			day_night_overlay.color = Color(0.35, 0.12, 0.32, 0.25)
		_:
			day_night_overlay.color = Color(0.0, 0.0, 0.0, 0.0)


func _register_initial_chunks() -> void:
	_loaded_chunks.clear()
	var chunk_size: int = int(_parsed_world["chunk_size"])
	for coordinate: Vector2i in _parsed_world["tiles"]:
		var chunk := Vector2i(
			floori(float(coordinate.x) / chunk_size),
			floori(float(coordinate.y) / chunk_size)
		)
		_loaded_chunks[chunk] = true
		api_client.mark_chunk_loaded(chunk)


func _request_chunks_around_camera() -> void:
	var chunk_size: int = int(_parsed_world["chunk_size"])
	var map_position: Vector2i = world_scene.renderer.local_to_map(camera.position)
	var center_chunk := Vector2i(
		floori(float(map_position.x) / chunk_size),
		floori(float(map_position.y) / chunk_size)
	)
	world_scene.renderer.set_visible_chunk_center(center_chunk)
	for offset_x in range(-1, 2):
		for offset_y in range(-1, 2):
			var chunk := center_chunk + Vector2i(offset_x, offset_y)
			if not _loaded_chunks.has(chunk):
				api_client.request_chunk(chunk)


func _on_chunk_loaded(chunk_position: Vector2i, parsed_world: Dictionary) -> void:
	_loaded_chunks[chunk_position] = true
	_parsed_world = parsed_world
	_update_player_entity()
	world_scene.render_parsed_world(_parsed_world)
	minimap.update_world(_parsed_world)
	hud.update_world_info(
		api_client.backend_url,
		int(_parsed_world["width"]),
		int(_parsed_world["height"]),
		int(_parsed_world["chunk_size"]),
		int(_parsed_world["seed"]),
		_parsed_world["tiles"].size(),
		_parsed_world["resources"].size()
	)


func _update_player_entity() -> void:
	_player_entity = {}
	if not _tracked_entity_id.is_empty():
		for entity: Dictionary in _parsed_world.get("entities", []):
			if str(entity.get("id", "")) == _tracked_entity_id:
				_player_entity = entity
				break
	if not _player_entity.is_empty():
		hud.update_player(_player_entity, _follow_player)
		return
	for entity: Dictionary in _parsed_world.get("entities", []):
		if "player" in entity.get("tags", []):
			_player_entity = entity
			_tracked_entity_id = str(entity.get("id", ""))
			break
	hud.update_player(_player_entity, _follow_player)


func _on_live_entities_received(entities: Array) -> void:
	if _parsed_world.is_empty():
		return
	_parsed_world["entities"] = entities.duplicate(true)
	world_scene.renderer.update_entities(entities)
	inspector.refresh_entities(entities, int(_parsed_world.get("chunk_size", 16)))
	minimap.update_entities(entities)
	_update_player_entity()


func _on_live_resources_received(resources: Array) -> void:
	if _parsed_world.is_empty():
		return
	var parsed_resources: Array = []
	for resource_data: Variant in resources:
		if not resource_data is Dictionary:
			continue
		var resource: Dictionary = resource_data
		parsed_resources.append(WorldLoader.parse_resource(resource))
	_parsed_world["resources"] = parsed_resources
	world_scene.renderer.update_resources(parsed_resources)


func _on_live_structures_received(structures: Array) -> void:
	if _parsed_world.is_empty():
		return
	_parsed_world["structures"] = structures
	world_scene.renderer.update_structures(structures)
	minimap.update_structures(structures)
	inspector.refresh_structures(structures)


func _open_admin() -> void:
	if _parsed_world.is_empty():
		admin_panel.display_error("Load a world before opening agent administration.")
		return
	admin_panel.open_page(int(_parsed_world["width"]), int(_parsed_world["height"]))


func _on_agent_created(entity: Dictionary) -> void:
	admin_panel.operation_complete("Created %s at (%s, %s)" % [entity.get("name", "agent"), entity.get("x", 0), entity.get("y", 0)])
	api_client.fetch_world()


func _on_agent_removed(entity: Dictionary) -> void:
	admin_panel.operation_complete("Removed %s" % str(entity.get("name", "agent")))
	api_client.fetch_world()
