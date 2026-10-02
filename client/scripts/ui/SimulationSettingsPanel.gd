extends Control
class_name SimulationSettingsPanel

## Runtime controls for the authoritative clock, climate and client visuals.

signal apply_requested(settings: Dictionary, tick_rate: float, visual_quality: String)
signal reset_requested()
signal new_world_requested(options: Dictionary)
signal world_restored()
signal pause_requested()

const STARTER_AVATAR_IDS := ["scout", "builder", "herbalist", "scholar", "cook", "miner", "fisher", "artisan"]

var _panel: PanelContainer
var _status: Label
var _tick_rate: SpinBox
var _ticks_per_day: SpinBox
var _current_hour: SpinBox
var _day_start: SpinBox
var _night_start: SpinBox
var _season: OptionButton
var _weather: OptionButton
var _weather_intensity: HSlider
var _weather_value: Label
var _auto_temperature: CheckButton
var _temperature: SpinBox
var _auto_wind: CheckButton
var _wind_speed: SpinBox
var _wind_direction: SpinBox
var _precipitation_radius: SpinBox
var _visual_quality: OptionButton
var _world_size: OptionButton
var _world_width: SpinBox
var _world_height: SpinBox
var _random_seed: CheckButton
var _world_seed: SpinBox
var _starter_avatar: OptionButton
var _new_world_dialog: ConfirmationDialog
var _tween: Tween


func _ready() -> void:
	_build()
	hide()


func open_panel(calendar: Dictionary, tick_rate: float, world: Dictionary = {}) -> void:
	_tick_rate.value = tick_rate
	if not calendar.is_empty():
		_current_hour.value = int(calendar.get("hour", 8))
	if not world.is_empty():
		_world_width.value = int(world.get("width", 64))
		_world_height.value = int(world.get("height", 64))
		_world_seed.value = int(world.get("seed", 0))
		_update_world_preset_from_dimensions()
	show()
	_panel.modulate.a = 0.0
	_panel.scale = Vector2(0.97, 0.97)
	_panel.pivot_offset = _panel.size * 0.5
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	_tween.tween_property(_panel, "modulate:a", 1.0, 0.18)
	_tween.tween_property(_panel, "scale", Vector2.ONE, 0.24)


func close_panel() -> void:
	if not visible:
		return
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	_tween.tween_property(_panel, "modulate:a", 0.0, 0.13)
	_tween.tween_property(_panel, "scale", Vector2(0.985, 0.985), 0.13)
	_tween.chain().tween_callback(hide)


func display_environment(data: Dictionary) -> void:
	var control: Dictionary = data.get("control", {})
	var calendar: Dictionary = data.get("calendar", {})
	_ticks_per_day.value = _number_or(control.get("ticks_per_day"), 24.0)
	_day_start.value = _number_or(control.get("day_start_hour"), 8.0)
	_night_start.value = _number_or(control.get("night_start_hour"), 20.0)
	_current_hour.value = _number_or(calendar.get("hour"), 8.0)
	_select_text(_season, _option_or_auto(control.get("season_override")))
	_select_text(_weather, _option_or_auto(control.get("weather_override")))
	_weather_intensity.value = _number_or(
		control.get("weather_intensity_override"),
		_number_or(calendar.get("weather_intensity"), 0.5)
	)
	var temperature_override: Variant = control.get("temperature_override_c")
	_auto_temperature.button_pressed = temperature_override == null
	_temperature.value = _number_or(
		temperature_override, _number_or(calendar.get("temperature_c"), 18.0)
	)
	var wind_speed_override: Variant = control.get("wind_speed_override")
	_auto_wind.button_pressed = wind_speed_override == null
	_wind_speed.value = _number_or(
		wind_speed_override, _number_or(calendar.get("wind_speed"), 4.0)
	)
	_wind_direction.value = _number_or(
		control.get("wind_direction_override"),
		_number_or(calendar.get("wind_direction"), 0.0)
	)
	_precipitation_radius.value = _number_or(
		control.get("precipitation_radius_override"),
		_number_or(calendar.get("precipitation_radius"), 10.0)
	)
	_update_enabled_controls()
	_status.text = "AUTHORITATIVE ENVIRONMENT SYNCHRONIZED"
	_status.add_theme_color_override("font_color", Color("72d6bb"))


static func _number_or(value: Variant, fallback: float) -> float:
	if value == null:
		return fallback
	if typeof(value) in [TYPE_INT, TYPE_FLOAT]:
		return float(value)
	return fallback


static func _option_or_auto(value: Variant) -> String:
	return "Auto" if value == null or str(value).is_empty() else str(value)


func display_error(message: String) -> void:
	_status.text = message
	_status.add_theme_color_override("font_color", Color("ef826f"))


func display_world_created(world: Dictionary) -> void:
	_status.text = "WORLD %d × %d CREATED · SEED %d" % [
		int(world.get("width", 0)), int(world.get("height", 0)), int(world.get("seed", 0))
	]
	_status.add_theme_color_override("font_color", Color("72d6bb"))


func _apply() -> void:
	var settings := {
		"ticks_per_day": int(_ticks_per_day.value),
		"current_hour": int(_current_hour.value),
		"day_start_hour": int(_day_start.value),
		"night_start_hour": int(_night_start.value),
		"season_override": null if _season.selected == 0 else _season.get_item_text(_season.selected).to_upper(),
		"weather_override": null if _weather.selected == 0 else _weather.get_item_text(_weather.selected).to_upper(),
		"weather_intensity_override": null if _weather.selected == 0 else _weather_intensity.value,
		"temperature_override_c": null if _auto_temperature.button_pressed else _temperature.value,
		"wind_speed_override": null if _auto_wind.button_pressed else _wind_speed.value,
		"wind_direction_override": null if _auto_wind.button_pressed else _wind_direction.value,
		"precipitation_radius_override": int(_precipitation_radius.value)
	}
	_status.text = "APPLYING CLOCK AND CLIMATE…"
	apply_requested.emit(settings, _tick_rate.value, _visual_quality.get_item_text(_visual_quality.selected).to_lower())


func _build() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.offset_top = 72
	shade.color = Color(0.01, 0.025, 0.035, 0.78)
	add_child(shade)
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.offset_left = 18
	_panel.offset_top = 76
	_panel.offset_right = -18
	_panel.offset_bottom = -18
	_panel.add_theme_stylebox_override("panel", _style(Color("07171ded"), Color("3a8a83"), 16))
	add_child(_panel)
	var margin := MarginContainer.new()
	for side: String in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	_panel.add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 13)
	margin.add_child(root)
	var header := HBoxContainer.new()
	root.add_child(header)
	var titles := VBoxContainer.new()
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(titles)
	var title := Label.new()
	title.text = "Settings / World & environment"
	title.add_theme_font_size_override("font_size", 25)
	title.add_theme_color_override("font_color", Color("f1e6cf"))
	titles.add_child(title)
	var subtitle := Label.new()
	subtitle.text = "Clock · seasons · weather · simulation cadence · visual load"
	subtitle.add_theme_color_override("font_color", Color("86a8ad"))
	titles.add_child(subtitle)
	var close := Button.new()
	close.text = "×  CLOSE"
	close.pressed.connect(close_panel)
	header.add_child(close)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	var content := VBoxContainer.new()
	content.custom_minimum_size.x = 0
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_theme_constant_override("separation", 12)
	scroll.add_child(content)
	var saves := preload("res://scripts/ui/CheckpointControls.gd").new()
	content.add_child(saves)
	saves.world_restored.connect(func() -> void: world_restored.emit())
	saves.pause_requested.connect(func() -> void: pause_requested.emit())
	var clock_grid := _section(content, "TIME & RHYTHM", "Set the pace of life. Citizens use these hours for sleep, work and survival.")
	_tick_rate = _spin(0.25, 8.0, 0.25, 1.0, "×")
	_add_field(clock_grid, "Simulation speed", _tick_rate)
	_ticks_per_day = _spin(12, 480, 1, 24, " ticks")
	_add_field(clock_grid, "Ticks in one day", _ticks_per_day)
	_current_hour = _spin(0, 23, 1, 8, ":00")
	_add_field(clock_grid, "Set current hour", _current_hour)
	_day_start = _spin(2, 12, 1, 8, ":00")
	_add_field(clock_grid, "Day begins", _day_start)
	_night_start = _spin(16, 23, 1, 20, ":00")
	_add_field(clock_grid, "Night begins", _night_start)
	var world_grid := _section(content, "NEW WORLD", "Create a fresh authoritative simulation. This replaces the active world and its citizens.")
	_world_size = _options(["Small · 32 × 32", "Standard · 64 × 64", "Large · 96 × 96", "Expansive · 128 × 128", "Custom"])
	_world_size.select(1)
	_world_size.item_selected.connect(_on_world_size_selected)
	_add_field(world_grid, "World scale", _world_size)
	_world_width = _spin(8, 128, 8, 64, " tiles")
	_world_height = _spin(8, 128, 8, 64, " tiles")
	var dimensions := HBoxContainer.new()
	dimensions.add_child(_world_width)
	var by := Label.new()
	by.text = "×"
	dimensions.add_child(by)
	dimensions.add_child(_world_height)
	_add_field(world_grid, "Dimensions", dimensions)
	_random_seed = CheckButton.new()
	_random_seed.text = "Discover a new seed"
	_random_seed.button_pressed = true
	_random_seed.toggled.connect(_update_seed_control)
	_world_seed = _spin(0, 2147483647, 1, 847291, "")
	var seed_row := HBoxContainer.new()
	seed_row.add_child(_random_seed)
	seed_row.add_child(_world_seed)
	_add_field(world_grid, "Terrain seed", seed_row)
	_starter_avatar = _options(["Aster", "Ember", "Fern", "Lumen", "Rowan", "Saffron", "Tide", "Violet"])
	_add_field(world_grid, "Starting appearance", _starter_avatar)
	var create_world := Button.new()
	create_world.text = "✦  CREATE FRESH WORLD"
	create_world.tooltip_text = "Replaces the current in-memory world after confirmation"
	create_world.pressed.connect(_confirm_new_world)
	_add_field(world_grid, "World lifecycle", create_world)
	var climate_grid := _section(content, "CLIMATE DIRECTOR", "Leave a field on Auto for procedural weather, or override it live.")
	_season = _options(["Auto", "Spring", "Summer", "Autumn", "Winter"])
	_add_field(climate_grid, "Season", _season)
	_weather = _options(["Auto", "Clear", "Rain", "Snow"])
	_weather.item_selected.connect(func(_index: int) -> void: _update_enabled_controls())
	_add_field(climate_grid, "Weather", _weather)
	var intensity_row := HBoxContainer.new()
	_weather_intensity = HSlider.new()
	_weather_intensity.min_value = 0.0
	_weather_intensity.max_value = 1.0
	_weather_intensity.step = 0.05
	_weather_intensity.value = 0.5
	_weather_intensity.custom_minimum_size.x = 190
	_weather_intensity.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_weather_value = Label.new()
	_weather_intensity.value_changed.connect(func(value: float) -> void: _weather_value.text = "%d%%" % roundi(value * 100.0))
	_weather_value.text = "50%"
	intensity_row.add_child(_weather_intensity)
	intensity_row.add_child(_weather_value)
	_add_field(climate_grid, "Rain / snow intensity", intensity_row)
	_auto_temperature = CheckButton.new()
	_auto_temperature.text = "Automatic"
	_auto_temperature.button_pressed = true
	_auto_temperature.toggled.connect(func(_enabled: bool) -> void: _update_enabled_controls())
	_temperature = _spin(-40, 55, 0.5, 18, " °C")
	var temperature_row := HBoxContainer.new()
	temperature_row.add_child(_auto_temperature)
	temperature_row.add_child(_temperature)
	_add_field(climate_grid, "Temperature", temperature_row)
	_auto_wind = CheckButton.new()
	_auto_wind.text = "Automatic"
	_auto_wind.button_pressed = true
	_auto_wind.toggled.connect(func(_enabled: bool) -> void: _update_enabled_controls())
	_wind_speed = _spin(0, 35, 0.5, 4, " m/s")
	_wind_direction = _spin(0, 359, 1, 0, "°")
	var wind_row := HBoxContainer.new()
	wind_row.add_child(_auto_wind)
	wind_row.add_child(_wind_speed)
	wind_row.add_child(_wind_direction)
	_add_field(climate_grid, "Wind speed / direction", wind_row)
	_precipitation_radius = _spin(2, 64, 1, 10, " tiles")
	_add_field(climate_grid, "Weather region", _precipitation_radius)
	var visual_grid := _section(content, "DISPLAY", "Tune ambient effects without changing simulation decisions.")
	_visual_quality = _options(["High", "Balanced", "Performance"])
	_add_field(visual_grid, "World effects", _visual_quality)
	var reduce_hover := CheckButton.new()
	reduce_hover.text = "Instant button feedback"
	reduce_hover.button_pressed = preload("res://scripts/ui/AtlasTheme.gd").reduced_motion
	reduce_hover.toggled.connect(func(enabled: bool) -> void:
		preload("res://scripts/ui/AtlasTheme.gd").reduced_motion = enabled
	)
	_add_field(visual_grid, "Reduce UI hover motion", reduce_hover)
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 8)
	root.add_child(footer)
	_status = Label.new()
	_status.text = "READY"
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_status.add_theme_color_override("font_color", Color("72d6bb"))
	footer.add_child(_status)
	var reset := Button.new()
	reset.text = "↺ NATURAL WORLD"
	reset.pressed.connect(func() -> void: reset_requested.emit())
	footer.add_child(reset)
	var apply := Button.new()
	apply.text = "APPLY TO SIMULATION"
	apply.custom_minimum_size.x = 190
	apply.pressed.connect(_apply)
	footer.add_child(apply)
	_new_world_dialog = ConfirmationDialog.new()
	_new_world_dialog.title = "Create a fresh world?"
	_new_world_dialog.dialog_text = "The active simulation world, citizens, structures and unsaved progress will be replaced."
	_new_world_dialog.ok_button_text = "CREATE WORLD"
	_new_world_dialog.confirmed.connect(_emit_new_world)
	add_child(_new_world_dialog)
	_on_world_size_selected(_world_size.selected)
	_update_seed_control(_random_seed.button_pressed)
	_update_enabled_controls()


func _on_world_size_selected(index: int) -> void:
	var sizes := [32, 64, 96, 128]
	var custom := index >= sizes.size()
	_world_width.editable = custom
	_world_height.editable = custom
	if not custom:
		_world_width.value = sizes[index]
		_world_height.value = sizes[index]


func _update_world_preset_from_dimensions() -> void:
	var width := int(_world_width.value)
	var height := int(_world_height.value)
	var sizes := [32, 64, 96, 128]
	var selected := 4
	if width == height and width in sizes:
		selected = sizes.find(width)
	_world_size.select(selected)
	_on_world_size_selected(selected)


func _update_seed_control(randomized: bool) -> void:
	_world_seed.editable = not randomized
	_world_seed.modulate = Color(1, 1, 1, 0.48 if randomized else 1.0)


func world_generation_options() -> Dictionary:
	var options := {
		"width": int(_world_width.value),
		"height": int(_world_height.value),
		"avatar_id": STARTER_AVATAR_IDS[_starter_avatar.selected],
	}
	if not _random_seed.button_pressed:
		options["seed"] = int(_world_seed.value)
	return options


func _confirm_new_world() -> void:
	var options := world_generation_options()
	var seed_text := "a random seed" if not options.has("seed") else "seed %d" % int(options.seed)
	_new_world_dialog.dialog_text = (
		"Create a %d × %d world using %s?\nStarting citizen: %s\n\nThe active world, citizens, structures and unsaved progress will be replaced."
		% [int(options.width), int(options.height), seed_text, _starter_avatar.get_item_text(_starter_avatar.selected)]
	)
	_new_world_dialog.popup_centered(Vector2i(520, 230))


func _emit_new_world() -> void:
	_status.text = "GENERATING FRESH WORLD…"
	_status.add_theme_color_override("font_color", Color("e7c36c"))
	new_world_requested.emit(world_generation_options())


func _section(parent: VBoxContainer, title_text: String, hint_text: String) -> GridContainer:
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _style(Color("10242ad9"), Color("26474d"), 10))
	parent.add_child(panel)
	var margin := MarginContainer.new()
	for side: String in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 13)
	panel.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 7)
	margin.add_child(column)
	var title := Label.new()
	title.text = title_text
	title.add_theme_color_override("font_color", Color("65dcc0"))
	title.add_theme_font_size_override("font_size", 16)
	column.add_child(title)
	var hint := Label.new()
	hint.text = hint_text
	hint.add_theme_color_override("font_color", Color("89a0a6"))
	column.add_child(hint)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 8)
	column.add_child(grid)
	return grid


func _add_field(grid: GridContainer, label_text: String, control: Control) -> void:
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size.x = 150
	label.add_theme_color_override("font_color", Color("c1ced0"))
	grid.add_child(label)
	control.custom_minimum_size.x = maxf(control.custom_minimum_size.x, 190.0)
	grid.add_child(control)


func _spin(minimum: float, maximum: float, step: float, initial: float, suffix: String) -> SpinBox:
	var spin := SpinBox.new()
	spin.min_value = minimum
	spin.max_value = maximum
	spin.step = step
	spin.value = initial
	spin.suffix = suffix
	return spin


func _options(items: Array[String]) -> OptionButton:
	var options := OptionButton.new()
	for item: String in items:
		options.add_item(item)
	return options


func _select_text(options: OptionButton, value: String) -> void:
	var normalized := value.to_lower()
	if normalized in ["", "<null>", "null", "none"]:
		normalized = "auto"
	for index in range(options.item_count):
		if options.get_item_text(index).to_lower() == normalized:
			options.select(index)
			return
	options.select(0)


func _update_enabled_controls() -> void:
	_weather_intensity.editable = _weather.selected != 0
	_temperature.editable = not _auto_temperature.button_pressed
	_wind_speed.editable = not _auto_wind.button_pressed
	_wind_direction.editable = not _auto_wind.button_pressed


func _style(background: Color, border: Color, radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(radius)
	style.shadow_color = Color(0, 0, 0, 0.45)
	style.shadow_size = 10
	return style
