# DebugHUD.gd
extends Control
class_name DebugHUD

## Visualizes client-side system metrics and active connection configurations.

signal reload_requested()
signal new_world_requested()
signal simulation_command_requested(command: String)
signal tick_rate_requested(ticks_per_second: float)
signal admin_requested()
signal crafting_requested()
signal observation_layer_requested(layer_name: String)
signal navigation_requested(mode: String)
signal focus_mode_requested(enabled: bool)
signal overview_visibility_changed(is_visible: bool)

@onready var menu_button: Button = $MenuButton
@onready var settings_menu: MenuButton = $SettingsMenu
@onready var menu_panel: PanelContainer = $MenuPanel
@onready var label_status: Label = $MenuPanel/MarginContainer/VBoxContainer/ConnectionStatus
@onready var label_url: Label = $MenuPanel/MarginContainer/VBoxContainer/BackendURL
@onready var label_size: Label = $MenuPanel/MarginContainer/VBoxContainer/WorldSize
@onready var label_chunk: Label = $MenuPanel/MarginContainer/VBoxContainer/ChunkSize
@onready var label_seed: Label = $MenuPanel/MarginContainer/VBoxContainer/WorldSeed
@onready var label_tiles: Label = $MenuPanel/MarginContainer/VBoxContainer/LoadedTileCount
@onready var label_resources: Label = $MenuPanel/MarginContainer/VBoxContainer/LoadedResourceCount
@onready var label_chunks: Label = $MenuPanel/MarginContainer/VBoxContainer/ChunkCount
@onready var label_fps: Label = $MenuPanel/MarginContainer/VBoxContainer/FPS
@onready var label_tps: Label = $MenuPanel/MarginContainer/VBoxContainer/TPS
@onready var label_simulation_state: Label = $MenuPanel/MarginContainer/VBoxContainer/SimulationState
@onready var label_tick: Label = $MenuPanel/MarginContainer/VBoxContainer/CurrentTick
@onready var label_calendar: Label = $MenuPanel/MarginContainer/VBoxContainer/CalendarStatus
@onready var start_button: Button = $MenuPanel/MarginContainer/VBoxContainer/SimulationButtons/Start
@onready var pause_button: Button = $MenuPanel/MarginContainer/VBoxContainer/SimulationButtons/PauseResume
@onready var step_button: Button = $MenuPanel/MarginContainer/VBoxContainer/SimulationButtons/Step
@onready var stop_button: Button = $MenuPanel/MarginContainer/VBoxContainer/SimulationButtons/Stop
@onready var rate_input: SpinBox = $MenuPanel/MarginContainer/VBoxContainer/RateControls/TickRate
@onready var apply_rate_button: Button = $MenuPanel/MarginContainer/VBoxContainer/RateControls/ApplyRate
@onready var retry_button: Button = $MenuPanel/MarginContainer/VBoxContainer/RetryButton

var _clock_label: Label
var _season_label: Label
var _weather_label: Label
var _simulation_badge: Label
var _world_summary: Label
var _ecology_summary: Label
var _systems_summary: Label
var _player_summary: Label
var _event_feed: RichTextLabel
var _event_lines: Array[String] = []
var _command_pause_button: Button
var _command_primary_button: Button
var _speed_buttons: Array[Button] = []
var _current_simulation_state := "STOPPED"
var _connection_dot: Label
var _status_rail: VBoxContainer
var _event_panel: PanelContainer
var _intel_button: Button
var _intel_visible := false
var _footer_citizens: Label
var _footer_buildings: Label
var _footer_resources: Label
var _footer_settlements: Label
var _footer_climate: Label
var _layer_menu: MenuButton
var _layer_names: Array[String] = []
var _focus_button: Button
var _focus_mode := false
var _main_header: PanelContainer
var _time_panel: PanelContainer
var _command_bar: PanelContainer
var _status_bar: PanelContainer
var _brand: VBoxContainer
var _motto: Label
var _debug_visible := false
var _agent_card: PanelContainer
var _agent_card_name: Label
var _agent_card_action: Label
var _agent_card_needs: Label
var _overview_scroll: ScrollContainer
var _nav_group := ButtonGroup.new()
var _overview_tween: Tween

func _ready() -> void:
	_build_command_hud()
	menu_button.hide()
	settings_menu.hide()
	menu_button.pressed.connect(_toggle_menu)
	_setup_settings_menu()
	retry_button.pressed.connect(_on_retry_pressed)
	start_button.pressed.connect(func() -> void: simulation_command_requested.emit("start"))
	pause_button.pressed.connect(_on_pause_resume_pressed)
	step_button.pressed.connect(func() -> void: simulation_command_requested.emit("step"))
	stop_button.pressed.connect(func() -> void: simulation_command_requested.emit("stop"))
	apply_rate_button.pressed.connect(func() -> void: tick_rate_requested.emit(rate_input.value))
	retry_button.hide()
	menu_panel.hide()
	_set_intel_visible(false)
	_push_event("World link initialized", Color("72d6bb"))
	get_viewport().size_changed.connect(_apply_responsive_layout)
	_apply_responsive_layout()
	call_deferred("_animate_hud_entry")

## Alters the visible connection state label color and text parameters.
func update_status(is_connected: bool, error_msg: String = "") -> void:
	if is_connected:
		label_status.text = "Connection Status: Connected"
		label_status.add_theme_color_override("font_color", Color.GREEN)
		retry_button.hide()
		_connection_dot.text = "● ONLINE"
		_connection_dot.add_theme_color_override("font_color", Color("72d6bb"))
	else:
		label_status.text = "Connection Status: Disconnected (%s)" % (error_msg if error_msg != "" else "Unavailable")
		label_status.add_theme_color_override("font_color", Color.RED)
		retry_button.show()
		_connection_dot.text = "● OFFLINE"
		_connection_dot.add_theme_color_override("font_color", Color("ef826f"))
		_push_event("Backend connection interrupted", Color("ef826f"))

## Displays metadata details fetched from the API response payload.
func update_world_info(url: String, width: int, height: int, chunk_size: int, world_seed: int, tiles_count: int, resources_count: int) -> void:
	label_url.text = "Backend URL: %s" % url
	label_size.text = "World Size: %d x %d" % [width, height]
	label_chunk.text = "Chunk Size: %d" % chunk_size
	label_seed.text = "World Seed: %d" % world_seed
	label_tiles.text = "Loaded Tile Count: %d" % tiles_count
	label_resources.text = "Loaded Resources: %d" % resources_count
	var loaded_chunks: int = ceili(float(tiles_count) / float(chunk_size * chunk_size))
	label_chunks.text = "Explored Chunks: %d" % loaded_chunks
	_world_summary.text = "WORLD  %d × %d\nSEED  %d\nSTREAMED  %d tiles · %d chunks\nNATURAL NODES  %d" % [
		width, height, world_seed, tiles_count, loaded_chunks, resources_count
	]
	_footer_resources.text = "▰  %d\nRESOURCES" % resources_count


func configure_observation_layers(layer_support: Dictionary) -> void:
	var popup := _layer_menu.get_popup()
	popup.clear()
	_layer_names.clear()
	for layer: String in ["terrain", "resources", "population", "fertility", "temperature", "humidity", "wealth", "knowledge", "influence", "trade_routes", "danger"]:
		var status := str(layer_support.get(layer, "not_implemented"))
		var caption := layer.replace("_", " ").to_upper()
		if status != "available":
			caption += "  ·  NOT AVAILABLE"
		popup.add_item(caption, _layer_names.size())
		popup.set_item_disabled(_layer_names.size(), status != "available")
		_layer_names.append(layer)


func update_simulation(state: String, tick: int, tick_rate: float) -> void:
	_current_simulation_state = state
	label_simulation_state.text = "Simulation: %s" % state.capitalize()
	label_tick.text = "Current Tick: %d" % tick
	label_tps.text = "TPS (Sim Rate): %.2f" % tick_rate
	rate_input.value = tick_rate
	pause_button.text = "Resume" if state == "PAUSED" else "Pause"
	_command_primary_button.text = "▶  RESUME" if state == "PAUSED" else ("Ⅱ  PAUSE" if state == "RUNNING" else "▶  BEGIN")
	start_button.disabled = state == "RUNNING"
	step_button.disabled = state == "RUNNING"
	_simulation_badge.text = "● %s   TICK %d   %.1f×" % [state, tick, tick_rate]
	_simulation_badge.add_theme_color_override(
		"font_color",
		Color("72d6bb") if state == "RUNNING" else Color("e9c978")
	)
	for speed_button: Button in _speed_buttons:
		var button_rate := float(speed_button.get_meta("rate", 1.0))
		var active := is_equal_approx(button_rate, tick_rate)
		speed_button.add_theme_color_override("font_color", Color("75e6b5") if active else Color("8fa6ad"))


func update_tick(tick: int) -> void:
	label_tick.text = "Current Tick: %d" % tick
	var current_state: String = label_simulation_state.text.trim_prefix("Simulation: ").to_upper()
	_simulation_badge.text = "● %s   TICK %d   %.1f×" % [current_state, tick, rate_input.value]


func update_calendar(calendar: Dictionary) -> void:
	label_calendar.text = "Day %d, %02d:00 — %s (%s)\n%s, %.1f C, wind %.1f" % [
		int(calendar.get("day", 1)),
		int(calendar.get("hour", 6)),
		str(calendar.get("season", "SPRING")).capitalize(),
		str(calendar.get("phase", "DAWN")).capitalize(),
		str(calendar.get("weather", "CLEAR")).capitalize(),
		float(calendar.get("temperature_c", 16.0)),
		float(calendar.get("wind_speed", 4.0))
	]
	var hour: int = int(calendar.get("hour", 6))
	_clock_label.text = "DAY %02d   %02d:00" % [int(calendar.get("day", 1)), hour]
	_season_label.text = "%s · %s" % [
		str(calendar.get("season", "SPRING")),
		str(calendar.get("phase", "DAWN"))
	]
	_weather_label.text = "%s   %.1f°C   HUM %.0f%%   WIND %.1f" % [
		str(calendar.get("weather", "CLEAR")),
		float(calendar.get("temperature_c", 16.0)),
		float(calendar.get("humidity", 0.5)) * 100.0,
		float(calendar.get("wind_speed", 4.0))
	]
	_footer_climate.text = "◉  %.1f°C   ◈  %.0f%%\n%s · %s" % [
		float(calendar.get("temperature_c", 16.0)),
		float(calendar.get("humidity", 0.5)) * 100.0,
		str(calendar.get("season", "SPRING")),
		str(calendar.get("phase", "DAWN"))
	]


func update_system_health(health: Dictionary) -> void:
	var resources: int = int(health.get("resources", 0))
	var depleted: int = int(health.get("depleted_resources", 0))
	var resource_ratio: float = float(health.get("average_resource_ratio", 0.0)) * 100.0
	_ecology_summary.text = "ECOLOGY\nRESOURCE HEALTH  %.0f%%\nAVAILABLE  %d · DEPLETED  %d\nWILDLIFE  %d · RESERVED  %d" % [
		resource_ratio,
		maxi(resources - depleted, 0),
		depleted,
		int(health.get("wildlife", 0)),
		int(health.get("reserved_resources", 0))
	]
	_systems_summary.text = "SIMULATION\nENTITIES  %d / %d active · GROUPS %d\nSTRUCTURES  %d / %d complete\nGOALS  %d · ACTIONS  %d · MESSAGES  %d" % [
		int(health.get("active_entities", 0)),
		int(health.get("entities", 0)),
		int(health.get("groups", 0)),
		int(health.get("completed_structures", 0)),
		int(health.get("structures", 0)),
		int(health.get("active_goals", 0)),
		int(health.get("active_actions", 0)),
		int(health.get("messages", 0))
	]
	_footer_citizens.text = "♟  %d\nCITIZENS" % int(health.get("citizens", health.get("active_entities", 0)))
	_footer_buildings.text = "⌂  %d\nBUILDINGS" % int(health.get("completed_structures", 0))
	_footer_settlements.text = "⚑  %d\nSETTLEMENTS" % int(health.get("groups", 0))


func update_player(entity: Dictionary, following: bool) -> void:
	if entity.is_empty():
		_player_summary.text = "AI PLAYER\nWaiting for autonomous entity…"
		_agent_card_name.text = "NO ACTIVE AITIZEN"
		_agent_card_action.text = "Waiting for an autonomous agent"
		_agent_card_needs.text = ""
		return
	var needs_value: Variant = entity.get("needs", {})
	var needs: Dictionary = needs_value if needs_value is Dictionary else {}
	var inventory_value: Variant = entity.get("inventory", {})
	var inventory_container: Dictionary = inventory_value if inventory_value is Dictionary else {}
	var inventory: Dictionary = inventory_container.get("items", {})
	var entity_kind := str(entity.get("kind", "agent")).to_lower()
	var role_label := "WILDLIFE" if entity_kind == "animal" else "AI PLAYER"
	var carried: Array[String] = []
	for item_type: Variant in inventory:
		carried.append("%s %.0f" % [str(item_type).capitalize(), float(inventory[item_type])])
	_player_summary.text = "%s  %s\nHP %.0f · HUNGER %.0f · THIRST %.0f · ENERGY %.0f\n%s → %s\nPACK  %s\n[F] %s CAMERA" % [
		role_label,
		str(entity.get("name", "Aitizen")),
		float(needs.get("health", 100.0)),
		float(needs.get("hunger", 0.0)),
		float(needs.get("thirst", 0.0)),
		float(needs.get("energy", 100.0)),
		str(entity.get("goal", "idle")).replace("_", " ").to_upper(),
		str(entity.get("action", "idle")).replace("_", " ").to_upper(),
		", ".join(carried) if not carried.is_empty() else "Empty",
		"RELEASE" if following else "FOLLOW"
	]
	_agent_card_name.text = "◉  %s" % str(entity.get("name", "Aitizen"))
	_agent_card_action.text = "%s  ·  %s  ·  %s" % [
		str(entity.get("goal", "idle")).replace("_", " ").to_upper(),
		str(entity.get("action", "idle")).replace("_", " ").to_upper(),
		"TRACKING" if following else "FREE CAMERA"
	]
	_agent_card_needs.text = "♥ %.0f   ◔ %.0f   ◇ %.0f   ⚡ %.0f    PACK %s" % [
		float(needs.get("health", 100.0)),
		float(needs.get("hunger", 0.0)),
		float(needs.get("thirst", 0.0)),
		float(needs.get("energy", 100.0)),
		", ".join(carried) if not carried.is_empty() else "EMPTY"
	]
func add_simulation_event(event_name: String, tick: int) -> void:
	var readable: String = event_name.replace(":", "  ·  ").replace("_", " ").to_upper()
	_push_event("T%05d  %s" % [tick, readable], Color("a8bac1"))

func _process(_delta: float) -> void:
	label_fps.text = "FPS: %d" % Engine.get_frames_per_second()

func _on_retry_pressed() -> void:
	reload_requested.emit()


func _on_pause_resume_pressed() -> void:
	var command := "resume" if pause_button.text == "Resume" else "pause"
	simulation_command_requested.emit(command)


func _toggle_menu() -> void:
	if not menu_panel.visible and _intel_visible:
		_set_intel_visible(false)
	menu_panel.visible = not menu_panel.visible
	menu_button.text = "Close" if menu_panel.visible else "Menu"


func toggle_settings() -> void:
	_toggle_menu()


func attach_minimap(minimap: Control) -> void:
	## Keep the map in the overview layout so it can never overlap telemetry cards.
	minimap.reparent(_status_rail)
	_status_rail.move_child(minimap, 2)
	minimap.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	minimap.custom_minimum_size = Vector2(214, 132)
	minimap.size = Vector2(214, 132)
	minimap.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	minimap.clip_contents = true


func _setup_settings_menu() -> void:
	var popup := settings_menu.get_popup()
	popup.add_item("New World", 1)
	popup.add_item("Reload World", 2)
	popup.add_separator()
	popup.add_item("Toggle World Intel", 3)
	popup.add_separator()
	popup.add_item("Agent Administration", 4)
	popup.add_separator()
	popup.add_item("Toggle Debug Telemetry", 5)
	popup.id_pressed.connect(_on_settings_item_pressed)


func _build_command_hud() -> void:
	var header := PanelContainer.new()
	_main_header = header
	header.name = "MainHeader"
	header.set_anchors_preset(Control.PRESET_TOP_WIDE)
	header.offset_left = 18.0
	header.offset_top = 12.0
	header.offset_right = -18.0
	header.offset_bottom = 76.0
	header.add_theme_stylebox_override("panel", _panel_style(Color("071722ed"), Color("286277"), 15))
	var header_style := header.get_theme_stylebox("panel") as StyleBoxFlat
	header_style.content_margin_left = 16
	header_style.content_margin_right = 16
	header_style.content_margin_top = 8
	header_style.content_margin_bottom = 8
	add_child(header)
	var header_row := HBoxContainer.new()
	header_row.add_theme_constant_override("separation", 8)
	header.add_child(header_row)
	var brand := VBoxContainer.new()
	_brand = brand
	brand.custom_minimum_size.x = 220
	header_row.add_child(brand)
	brand.add_child(_hud_label("AITIZEN REALM", 22, Color("ecdfbb")))
	brand.add_child(_hud_label("FIELD OBSERVATORY  /  LIVE WORLD", 9, Color("a6b6a1")))
	var nav := HBoxContainer.new()
	nav.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.alignment = BoxContainer.ALIGNMENT_CENTER
	nav.add_theme_constant_override("separation", 5)
	header_row.add_child(nav)
	nav.add_child(_nav_button("World", func() -> void: navigation_requested.emit("world"), true))
	nav.add_child(_nav_button("Citizens", func() -> void: navigation_requested.emit("citizens")))
	nav.add_child(_nav_button("Build", func() -> void: navigation_requested.emit("build")))
	nav.add_child(_nav_button("Research", func() -> void: navigation_requested.emit("research")))
	nav.add_child(_nav_button("Journal", func() -> void: navigation_requested.emit("history")))
	nav.add_child(_nav_button("Settings", func() -> void: navigation_requested.emit("settings")))
	var motto := _hud_label("“From simple agents…\nto complex civilizations.”", 12, Color("b8c7cc"))
	_motto = motto
	motto.custom_minimum_size.x = 220
	motto.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	motto.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	header_row.add_child(motto)

	var top_bar := PanelContainer.new()
	_time_panel = top_bar
	top_bar.name = "CommandTopBar"
	top_bar.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	top_bar.position = Vector2(-468, 88)
	top_bar.size = Vector2(450, 58)
	top_bar.add_theme_stylebox_override("panel", _panel_style(Color("091419e8"), Color("31535d"), 12))
	add_child(top_bar)
	var top_margin := MarginContainer.new()
	top_margin.add_theme_constant_override("margin_left", 20)
	top_margin.add_theme_constant_override("margin_top", 9)
	top_margin.add_theme_constant_override("margin_right", 20)
	top_margin.add_theme_constant_override("margin_bottom", 8)
	top_bar.add_child(top_margin)
	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 10)
	top_margin.add_child(top_row)
	_clock_label = _hud_label("DAY 01   06:00", 18, Color("f3e8d2"))
	_clock_label.custom_minimum_size.x = 105
	top_row.add_child(_clock_label)
	var center_column := VBoxContainer.new()
	center_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_row.add_child(center_column)
	_season_label = _hud_label("SPRING · DAWN", 12, Color("72d6bb"))
	_season_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center_column.add_child(_season_label)
	_weather_label = _hud_label("RAIN   14.2°C   WIND 7.2", 13, Color("b9cad0"))
	_weather_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center_column.add_child(_weather_label)
	_connection_dot = _hud_label("● LINKING", 11, Color("e9c978"))
	_connection_dot.custom_minimum_size.x = 55
	_connection_dot.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_connection_dot.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	top_row.add_child(_connection_dot)

	_overview_scroll = ScrollContainer.new()
	_overview_scroll.name = "OverviewDrawer"
	_overview_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	add_child(_overview_scroll)
	_status_rail = VBoxContainer.new()
	_status_rail.name = "WorldStatusRail"
	_status_rail.position = Vector2(18, 122)
	_status_rail.size = Vector2(214, 560)
	_status_rail.custom_minimum_size.x = 214
	_status_rail.clip_contents = true
	_status_rail.add_theme_constant_override("separation", 7)
	_overview_scroll.add_child(_status_rail)
	var heading := _hud_label("◉  WORLD OVERVIEW", 13, Color("72d6bb"))
	_status_rail.add_child(heading)
	_layer_menu = MenuButton.new()
	_layer_menu.text = "LAYERS  ·  TERRAIN  ▾"
	_layer_menu.custom_minimum_size = Vector2(214, 30)
	_layer_menu.get_popup().id_pressed.connect(_on_layer_selected)
	_status_rail.add_child(_layer_menu)
	_world_summary = _add_status_card(_status_rail, "WORLD\nWaiting for terrain stream…")
	_ecology_summary = _add_status_card(_status_rail, "ECOLOGY\nWaiting for resource telemetry…")
	_systems_summary = _add_status_card(_status_rail, "SIMULATION\nWaiting for backend state…")
	_player_summary = _add_status_card(_status_rail, "AI PLAYER\nWaiting for autonomous entity…")

	var command_bar := PanelContainer.new()
	_command_bar = command_bar
	command_bar.name = "TimeControls"
	command_bar.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	command_bar.position = Vector2(-286, -84)
	command_bar.size = Vector2(572, 64)
	command_bar.add_theme_stylebox_override("panel", _panel_style(Color("07151bf4"), Color("46a899"), 18))
	add_child(command_bar)
	var command_margin := MarginContainer.new()
	command_margin.add_theme_constant_override("margin_left", 12)
	command_margin.add_theme_constant_override("margin_top", 8)
	command_margin.add_theme_constant_override("margin_right", 12)
	command_margin.add_theme_constant_override("margin_bottom", 8)
	command_bar.add_child(command_margin)
	var controls := HBoxContainer.new()
	controls.alignment = BoxContainer.ALIGNMENT_CENTER
	controls.add_theme_constant_override("separation", 6)
	command_margin.add_child(controls)
	var state_stack := VBoxContainer.new()
	state_stack.custom_minimum_size.x = 132
	state_stack.add_theme_constant_override("separation", 0)
	controls.add_child(state_stack)
	state_stack.add_child(_hud_label("SIMULATION CONTROL", 9, Color("d4bd87")))
	_simulation_badge = _hud_label("● READY  ·  TICK 0", 11, Color("e9c978"))
	_simulation_badge.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	state_stack.add_child(_simulation_badge)
	_command_primary_button = _command_button("▶  BEGIN", _on_primary_transport_pressed, Vector2(104, 42), true)
	controls.add_child(_command_primary_button)
	_command_pause_button = _command_primary_button
	var step_control := _command_button("›|", func() -> void: simulation_command_requested.emit("step"), Vector2(42, 42))
	step_control.tooltip_text = "Advance one simulation tick"
	controls.add_child(step_control)
	var stop_control := _command_button("■", func() -> void: simulation_command_requested.emit("stop"), Vector2(42, 42))
	stop_control.tooltip_text = "Stop and reset the clock"
	controls.add_child(stop_control)
	var divider := VSeparator.new()
	divider.custom_minimum_size.x = 8
	controls.add_child(divider)
	var speed_stack := VBoxContainer.new()
	speed_stack.add_theme_constant_override("separation", 1)
	controls.add_child(speed_stack)
	speed_stack.add_child(_hud_label("TIME FLOW", 9, Color("789098")))
	var speeds := HBoxContainer.new()
	speeds.add_theme_constant_override("separation", 2)
	speed_stack.add_child(speeds)
	for preset_rate: float in [0.5, 1.0, 2.0, 4.0]:
		var speed_button := _command_button("%s×" % str(preset_rate), func() -> void: tick_rate_requested.emit(preset_rate), Vector2(42, 25))
		speed_button.set_meta("rate", preset_rate)
		_speed_buttons.append(speed_button)
		speeds.add_child(speed_button)

	_event_panel = PanelContainer.new()
	_event_panel.name = "EventFeed"
	_event_panel.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_event_panel.position = Vector2(18, -210)
	_event_panel.size = Vector2(214, 190)
	_event_panel.add_theme_stylebox_override("panel", _panel_style(Color("091419dc"), Color("243b43"), 9))
	add_child(_event_panel)
	_event_feed = RichTextLabel.new()
	_event_feed.bbcode_enabled = true
	_event_feed.fit_content = false
	_event_feed.scroll_active = false
	_event_feed.add_theme_font_size_override("normal_font_size", 11)
	_event_feed.add_theme_constant_override("line_separation", 4)
	_event_panel.add_child(_event_feed)

	var footer := PanelContainer.new()
	_status_bar = footer
	footer.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	footer.position = Vector2(-405, -42)
	footer.size = Vector2(810, 34)
	footer.add_theme_stylebox_override("panel", _panel_style(Color("071722ed"), Color("8b7438"), 9))
	add_child(footer)
	footer.hide()
	var footer_row := HBoxContainer.new()
	footer_row.alignment = BoxContainer.ALIGNMENT_CENTER
	footer_row.add_theme_constant_override("separation", 28)
	footer.add_child(footer_row)
	_footer_citizens = _footer_label("♟  0\nCITIZENS")
	_footer_buildings = _footer_label("⌂  0\nBUILDINGS")
	_footer_resources = _footer_label("▰  0\nRESOURCES")
	_footer_settlements = _footer_label("⚑  0\nSETTLEMENTS")
	_footer_climate = _footer_label("◉  16°C\nSPRING · DAWN")
	for item: Label in [_footer_citizens, _footer_buildings, _footer_resources, _footer_settlements, _footer_climate]:
		footer_row.add_child(item)

	_intel_button = _command_button("Overview", func() -> void: _set_intel_visible(not _intel_visible))
	_intel_button.text = "×  HIDE OVERVIEW"
	_intel_button.set_anchors_preset(Control.PRESET_TOP_LEFT)
	_intel_button.position = Vector2(18, 88)
	_intel_button.size = Vector2(214, 32)
	add_child(_intel_button)

	_agent_card = PanelContainer.new()
	_agent_card.name = "AgentFocusCard"
	_agent_card.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_agent_card.position = Vector2(18, -122)
	_agent_card.size = Vector2(214, 104)
	_agent_card.add_theme_stylebox_override("panel", _panel_style(Color("08171def"), Color("3a887c"), 10))
	add_child(_agent_card)
	var agent_margin := MarginContainer.new()
	for side in ["margin_left", "margin_top", "margin_right", "margin_bottom"]:
		agent_margin.add_theme_constant_override(side, 10)
	_agent_card.add_child(agent_margin)
	var agent_column := VBoxContainer.new()
	agent_column.add_theme_constant_override("separation", 3)
	agent_margin.add_child(agent_column)
	_agent_card_name = _hud_label("NO ACTIVE AITIZEN", 13, Color("72d6bb"))
	_agent_card_action = _hud_label("Waiting for autonomy", 11, Color("e8dfcc"))
	_agent_card_needs = _hud_label("", 9, Color("a9bdc2"))
	_agent_card_needs.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	agent_column.add_child(_agent_card_name)
	agent_column.add_child(_agent_card_action)
	agent_column.add_child(_agent_card_needs)

	_focus_button = _command_button("Hide interface", _toggle_focus_mode)
	_focus_button.text = "⛶  WORLD FOCUS"
	_focus_button.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_focus_button.position = Vector2(-166, 158)
	_focus_button.size = Vector2(148, 32)
	add_child(_focus_button)


func _add_status_card(parent: VBoxContainer, initial_text: String) -> Label:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(214, 82)
	panel.add_theme_stylebox_override("panel", _panel_style(Color("0c1a20df"), Color("29434b"), 8))
	parent.add_child(panel)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 9)
	panel.add_child(margin)
	var label := _hud_label(initial_text, 12, Color("b8c7cc"))
	label.add_theme_constant_override("line_spacing", 3)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	label.custom_minimum_size = Vector2(184, 108)
	label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	margin.add_child(label)
	return label


func _command_button(caption: String, callback: Callable, minimum_size: Vector2 = Vector2(70, 32), primary: bool = false) -> Button:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size = minimum_size
	button.add_theme_font_size_override("font_size", 11)
	button.add_theme_color_override("font_color", Color("dbe6e4"))
	button.add_theme_stylebox_override("normal", _panel_style(Color("0d534d") if primary else Color("14272e"), Color("64d5bc") if primary else Color("31535d"), 10))
	button.add_theme_stylebox_override("hover", _panel_style(Color("1b3b43"), Color("72d6bb"), 6))
	button.pressed.connect(callback)
	_bind_control_animation(button)
	return button


func _bind_control_animation(control: Control) -> void:
	control.mouse_entered.connect(func() -> void:
		var tween := create_tween()
		tween.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(control, "modulate", Color("c8fff2"), 0.12)
	)
	control.mouse_exited.connect(func() -> void:
		var tween := create_tween()
		tween.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(control, "modulate", Color.WHITE, 0.18)
	)


func _animate_hud_entry() -> void:
	var final_position := _command_bar.position
	_command_bar.position += Vector2(0, 22)
	_command_bar.modulate = Color(1, 1, 1, 0)
	var tween := create_tween().set_parallel(true)
	tween.set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	tween.tween_property(_command_bar, "position", final_position, 0.42)
	tween.tween_property(_command_bar, "modulate", Color.WHITE, 0.28)


func _on_primary_transport_pressed() -> void:
	match _current_simulation_state:
		"RUNNING": simulation_command_requested.emit("pause")
		"PAUSED": simulation_command_requested.emit("resume")
		_: simulation_command_requested.emit("start")


func _nav_button(caption: String, callback: Callable, active: bool = false) -> Button:
	var button := Button.new()
	button.text = caption
	button.custom_minimum_size = Vector2(76, 40)
	button.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	button.toggle_mode = true
	button.button_group = _nav_group
	button.button_pressed = active
	button.add_theme_font_size_override("font_size", 11)
	button.add_theme_color_override("font_color", Color("e4eef0"))
	var normal_color := Color("202a26")
	var border_color := Color("3d4a40")
	button.add_theme_stylebox_override("normal", _panel_style(normal_color, border_color, 9))
	button.add_theme_stylebox_override("hover", _panel_style(Color("12384a"), Color("72d6bb"), 9))
	button.add_theme_stylebox_override("pressed", _panel_style(Color("46513b"), Color("d4bd87"), 9))
	_bind_control_animation(button)
	button.pressed.connect(callback)
	return button


func _footer_label(caption: String) -> Label:
	var label := _hud_label(caption, 10, Color("d8e3df"))
	label.custom_minimum_size = Vector2(116, 30)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return label


func _hud_label(caption: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = caption
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label


func _panel_style(background: Color, border: Color, radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(background.r * 0.65 + 0.045, background.g * 0.65 + 0.035, background.b * 0.45 + 0.025, 0.97)
	style.border_color = Color(border.r * 0.6 + 0.13, border.g * 0.5 + 0.1, border.b * 0.3 + 0.07)
	style.set_border_width_all(1)
	style.set_corner_radius_all(mini(radius, 8))
	style.shadow_color = Color(0, 0, 0, 0.28)
	style.shadow_size = 5
	return style


func _push_event(message: String, color: Color) -> void:
	var color_hex: String = color.to_html(false)
	_event_lines.push_front("[color=#%s]%s[/color]" % [color_hex, message])
	if _event_lines.size() > 6:
		_event_lines.resize(6)
	if _event_feed != null:
		_event_feed.text = "[color=#72d6bb][b]LIVE EVENT STREAM[/b][/color]\n" + "\n".join(_event_lines)


func _set_intel_visible(is_visible: bool) -> void:
	if is_visible and menu_panel.visible:
		menu_panel.hide()
		menu_button.text = "Menu"
	_intel_visible = is_visible
	_status_rail.visible = is_visible
	_overview_scroll.visible = is_visible
	if _overview_tween != null:
		_overview_tween.kill()
	if is_visible:
		_overview_scroll.modulate.a = 0.0
		_overview_tween = create_tween()
		_overview_tween.tween_property(_overview_scroll, "modulate:a", 1.0, 0.22)
	_event_panel.visible = is_visible and _debug_visible
	_agent_card.visible = not is_visible and not _focus_mode
	_intel_button.text = "Close overview  ×" if is_visible else "World overview  +"
	overview_visibility_changed.emit(is_visible)


func apply_world_focus(enabled: bool) -> void:
	_focus_mode = enabled
	_main_header.visible = not enabled
	_time_panel.visible = not enabled
	_command_bar.visible = not enabled
	_status_bar.visible = false
	_status_rail.visible = not enabled and _intel_visible
	_overview_scroll.visible = not enabled and _intel_visible
	_event_panel.visible = not enabled and _intel_visible and _debug_visible
	_intel_button.visible = not enabled
	_agent_card.visible = not enabled and not _intel_visible
	_focus_button.text = "⛶  RESTORE UI" if enabled else "⛶  WORLD FOCUS"
	focus_mode_requested.emit(enabled)


func _toggle_focus_mode() -> void:
	apply_world_focus(not _focus_mode)


func _apply_responsive_layout() -> void:
	if _main_header == null:
		return
	var viewport_size := get_viewport_rect().size
	_motto.visible = viewport_size.x >= 1500.0
	_brand.custom_minimum_size.x = 220.0
	_brand.visible = viewport_size.x >= 850.0
	_main_header.get_child(0).alignment = BoxContainer.ALIGNMENT_CENTER
	_main_header.get_child(0).add_theme_constant_override("separation", 20)
	_overview_scroll.position = Vector2(18, 132)
	_overview_scroll.size = Vector2(234, maxf(140, viewport_size.y - 154))
	_command_bar.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_command_bar.position = Vector2(viewport_size.x - 590, viewport_size.y - 84)
	_agent_card.position = Vector2(18, viewport_size.y - 126)
	_time_panel.size = Vector2(450, 58)
	_status_bar.visible = false
	if viewport_size.x < 1380.0:
		for child: Control in _main_header.get_child(0).get_child(1).get_children():
			child.custom_minimum_size.x = 66.0


func _on_settings_item_pressed(item_id: int) -> void:
	match item_id:
		1:
			new_world_requested.emit()
		2:
			reload_requested.emit()
		3:
			_set_intel_visible(not _intel_visible)
		4:
			admin_requested.emit()
		5:
			_debug_visible = not _debug_visible
			_event_panel.visible = _debug_visible and _intel_visible and not _focus_mode


func _on_layer_selected(item_id: int) -> void:
	if item_id < 0 or item_id >= _layer_names.size():
		return
	var layer := _layer_names[item_id]
	_layer_menu.text = "LAYERS  ·  %s  ▾" % layer.replace("_", " ").to_upper()
	observation_layer_requested.emit(layer)
	_push_event("Observer layer: %s" % layer.replace("_", " ").capitalize(), Color("72d6bb"))
