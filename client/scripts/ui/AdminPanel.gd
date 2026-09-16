extends Control
class_name AdminPanel

## Full agent administration page built from live backend entity records.

signal create_agent_requested(name: String, x: int, y: int, radius: int, autonomous: bool)
signal remove_agent_requested(entity_id: String)
signal refresh_requested()

var _list: VBoxContainer
var _name_input: LineEdit
var _x_input: SpinBox
var _y_input: SpinBox
var _radius_input: SpinBox
var _autonomous_input: CheckButton
var _status: Label
var _count: Label


func _ready() -> void:
	_build_page()
	hide()


func open_page(world_width: int, world_height: int) -> void:
	_x_input.max_value = maxi(world_width - 1, 0)
	_y_input.max_value = maxi(world_height - 1, 0)
	_x_input.value = world_width / 2.0
	_y_input.value = world_height / 2.0
	show()
	refresh_requested.emit()


func close_page() -> void:
	hide()


func display_agents(entities: Array) -> void:
	for child: Node in _list.get_children():
		child.queue_free()
	_count.text = "%d ACTIVE" % entities.size()
	for entity_value: Variant in entities:
		if typeof(entity_value) == TYPE_DICTIONARY:
			_add_agent_row(entity_value as Dictionary)
	_status.text = "Live agent registry synchronized"
	_status.add_theme_color_override("font_color", Color("72d6bb"))


func display_error(message: String) -> void:
	_status.text = message
	_status.add_theme_color_override("font_color", Color("ef826f"))


func operation_complete(message: String) -> void:
	_status.text = message
	refresh_requested.emit()


func _build_page() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.015, 0.025, 0.03, 0.82)
	add_child(shade)

	var page := PanelContainer.new()
	page.set_anchors_preset(Control.PRESET_CENTER)
	page.position = Vector2(-430, -300)
	page.size = Vector2(860, 600)
	page.add_theme_stylebox_override("panel", _style(Color("0a171ceF"), Color("3b686d"), 14))
	add_child(page)
	var margin := MarginContainer.new()
	for side: String in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 22)
	page.add_child(margin)
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 12)
	margin.add_child(layout)

	var header := HBoxContainer.new()
	layout.add_child(header)
	var title := Label.new()
	title.text = "AGENT ADMINISTRATION"
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", 25)
	title.add_theme_color_override("font_color", Color("f1e6cf"))
	header.add_child(title)
	_count = Label.new()
	_count.text = "SYNCING"
	_count.add_theme_color_override("font_color", Color("72d6bb"))
	header.add_child(_count)
	var close := Button.new()
	close.text = "×"
	close.custom_minimum_size = Vector2(42, 38)
	close.pressed.connect(close_page)
	header.add_child(close)

	var subtitle := Label.new()
	subtitle.text = "Create and inspect backend-owned minds. Autonomous agents perceive, decide and act without direct orders."
	subtitle.add_theme_color_override("font_color", Color("9db0b6"))
	layout.add_child(subtitle)

	var form_panel := PanelContainer.new()
	form_panel.add_theme_stylebox_override("panel", _style(Color("102229"), Color("29474e"), 9))
	layout.add_child(form_panel)
	var form := HBoxContainer.new()
	form.add_theme_constant_override("separation", 8)
	form_panel.add_child(form)
	_name_input = LineEdit.new()
	_name_input.placeholder_text = "Agent name"
	_name_input.text = "New Aitizen"
	_name_input.custom_minimum_size.x = 180
	form.add_child(_name_input)
	_x_input = _number_input(" X", 0, 4096, 32)
	form.add_child(_x_input)
	_y_input = _number_input(" Y", 0, 4096, 32)
	form.add_child(_y_input)
	_radius_input = _number_input(" Vision", 1, 32, 8)
	form.add_child(_radius_input)
	_autonomous_input = CheckButton.new()
	_autonomous_input.text = "Autonomous"
	_autonomous_input.button_pressed = true
	form.add_child(_autonomous_input)
	var add_button := Button.new()
	add_button.text = "+ ADD AGENT"
	add_button.pressed.connect(_submit_agent)
	form.add_child(add_button)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(scroll)
	_list = VBoxContainer.new()
	_list.custom_minimum_size.x = 790
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 8)
	scroll.add_child(_list)
	var footer := HBoxContainer.new()
	layout.add_child(footer)
	_status = Label.new()
	_status.text = "Waiting for agent registry…"
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	footer.add_child(_status)
	var refresh := Button.new()
	refresh.text = "REFRESH"
	refresh.pressed.connect(func() -> void: refresh_requested.emit())
	footer.add_child(refresh)


func _add_agent_row(entity: Dictionary) -> void:
	var row_panel := PanelContainer.new()
	row_panel.custom_minimum_size.y = 104
	row_panel.add_theme_stylebox_override("panel", _style(Color("102128"), Color("27434a"), 8))
	_list.add_child(row_panel)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	row_panel.add_child(row)
	var identity := VBoxContainer.new()
	identity.custom_minimum_size.x = 190
	row.add_child(identity)
	var name_label := Label.new()
	name_label.text = str(entity.get("name", "Unknown"))
	name_label.add_theme_font_size_override("font_size", 17)
	name_label.add_theme_color_override("font_color", Color("f1e6cf"))
	identity.add_child(name_label)
	var tags: Array = entity.get("tags", [])
	var mode := Label.new()
	mode.text = "%s  ·  %s  ·  (%d, %d)  ·  VISION %d" % [
		"AUTONOMOUS" if "autonomous" in tags else "MANUAL",
		str(entity.get("profession", "generalist")).replace("_", " ").to_upper(),
		int(entity.get("x", 0)), int(entity.get("y", 0)),
		int(entity.get("perception_radius", 0))
	]
	mode.add_theme_color_override("font_color", Color("72d6bb"))
	identity.add_child(mode)

	var needs: Dictionary = entity.get("needs", {})
	var vitals := Label.new()
	vitals.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vitals.text = "HEALTH  %.0f   HUNGER  %.0f   THIRST  %.0f   ENERGY  %.0f\nGOAL  %s   →   ACTION  %s  %.0f%%\nKNOWLEDGE  %d tiles · %d resources · GROUP %s" % [
		float(needs.get("health", 100)), float(needs.get("hunger", 0)),
		float(needs.get("thirst", 0)), float(needs.get("energy", 100)),
		str(entity.get("goal", "idle")).replace("_", " ").to_upper(),
		str(entity.get("action", "idle")).replace("_", " ").to_upper(),
		float(entity.get("action_progress", 0.0)) * 100.0,
		int(entity.get("knowledge", {}).get("tiles", 0)),
		int(entity.get("knowledge", {}).get("resources", 0)),
		str(entity.get("group_id", "—")).left(8)
	]
	vitals.add_theme_color_override("font_color", Color("b4c4c9"))
	row.add_child(vitals)
	var remove := Button.new()
	remove.text = "REMOVE"
	remove.disabled = "player" in tags
	remove.tooltip_text = "The primary player cannot be removed." if remove.disabled else "Deactivate this agent"
	var entity_id := str(entity.get("id", ""))
	remove.pressed.connect(func() -> void: remove_agent_requested.emit(entity_id))
	row.add_child(remove)


func _submit_agent() -> void:
	var agent_name := _name_input.text.strip_edges()
	if agent_name.is_empty():
		display_error("Agent name cannot be empty.")
		return
	create_agent_requested.emit(
		agent_name,
		roundi(_x_input.value),
		roundi(_y_input.value),
		roundi(_radius_input.value),
		_autonomous_input.button_pressed
	)
	_status.text = "Creating %s…" % agent_name


func _number_input(suffix: String, minimum: float, maximum: float, value: float) -> SpinBox:
	var input := SpinBox.new()
	input.min_value = minimum
	input.max_value = maximum
	input.value = value
	input.suffix = suffix
	input.custom_minimum_size.x = 90
	return input


func _style(background: Color, border: Color, radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(radius)
	style.content_margin_left = 14
	style.content_margin_top = 10
	style.content_margin_right = 14
	style.content_margin_bottom = 10
	return style
