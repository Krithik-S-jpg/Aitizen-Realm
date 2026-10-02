extends Control
class_name AdminPanel

## Full agent administration page built from live backend entity records.

signal create_agent_requested(name: String, x: int, y: int, radius: int, autonomous: bool, avatar_id: String)
signal remove_agent_requested(entity_id: String)
signal refresh_requested()
signal focus_requested(position: Vector2i)

const CITIZEN_AVATARS: Array[Dictionary] = [
	{"id": "scout", "name": "Aster", "tint": "1fa9ad"},
	{"id": "builder", "name": "Ember", "tint": "d86835"},
	{"id": "herbalist", "name": "Fern", "tint": "6f9f45"},
	{"id": "scholar", "name": "Lumen", "tint": "536bd5"},
	{"id": "cook", "name": "Rowan", "tint": "b94750"},
	{"id": "miner", "name": "Saffron", "tint": "d79b22"},
	{"id": "fisher", "name": "Tide", "tint": "389fd8"},
	{"id": "artisan", "name": "Violet", "tint": "8556c9"}
]

var _list: VBoxContainer
var _name_input: LineEdit
var _x_input: SpinBox
var _y_input: SpinBox
var _radius_input: SpinBox
var _autonomous_input: CheckButton
var _status: Label
var _count: Label
var _table: Tree
var _search: LineEdit
var _details: RichTextLabel
var _agents: Array = []
var _selection: Dictionary = {}
var _page: PanelContainer
var _avatar_id := "scout"
var _avatar_texture: Texture2D
var _avatar_buttons: Dictionary = {}
var _creator_content: VBoxContainer
var _creator_toggle: Button


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
	_agents = entities.filter(func(value: Variant) -> bool:
		return value is Dictionary and str(value.get("kind", "agent")).to_lower() == "agent"
	)
	_rebuild_table()
	_inspect_selected()
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
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.offset_top = 72
	shade.color = Color(0.015, 0.025, 0.03, 0.82)
	add_child(shade)

	var page := PanelContainer.new()
	_page = page
	page.set_anchors_preset(Control.PRESET_FULL_RECT)
	page.offset_left = 18
	page.offset_top = 76
	page.offset_right = -18
	page.offset_bottom = -18
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
	title.text = "Citizens"
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
	subtitle.text = "Observe individual lives, decisions and needs. Select a citizen to inspect."
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	subtitle.add_theme_color_override("font_color", Color("9db0b6"))
	layout.add_child(subtitle)

	var form_panel := PanelContainer.new()
	form_panel.add_theme_stylebox_override("panel", _style(Color("102229"), Color("29474e"), 9))
	layout.add_child(form_panel)
	var creator_shell := VBoxContainer.new()
	creator_shell.add_theme_constant_override("separation", 8)
	form_panel.add_child(creator_shell)
	_creator_toggle = Button.new()
	_creator_toggle.text = "＋  CREATE A CITIZEN"
	_creator_toggle.alignment = HORIZONTAL_ALIGNMENT_LEFT
	_creator_toggle.tooltip_text = "Open the appearance and citizen creation controls"
	_creator_toggle.pressed.connect(_toggle_creator)
	creator_shell.add_child(_creator_toggle)
	var creator := VBoxContainer.new()
	_creator_content = creator
	creator.add_theme_constant_override("separation", 8)
	creator.visible = false
	creator_shell.add_child(creator)
	var creator_title := Label.new()
	creator_title.text = "CREATE A CITIZEN  ·  CHOOSE AN APPEARANCE"
	creator_title.add_theme_color_override("font_color", Color("72d6bb"))
	creator.add_child(creator_title)
	var avatar_row := HFlowContainer.new()
	avatar_row.add_theme_constant_override("h_separation", 6)
	avatar_row.add_theme_constant_override("v_separation", 6)
	creator.add_child(avatar_row)
	_avatar_texture = load("res://assets/pixel_art/aitizen_character_actions_v4_24f_clean.png") as Texture2D
	var avatar_group := ButtonGroup.new()
	for index: int in range(CITIZEN_AVATARS.size()):
		var profile: Dictionary = CITIZEN_AVATARS[index]
		var profile_id := str(profile["id"])
		var avatar_card := PanelContainer.new()
		avatar_card.custom_minimum_size = Vector2(104, 112)
		avatar_card.add_theme_stylebox_override("panel", _style(Color("0b1b21"), Color("29474e"), 8))
		avatar_row.add_child(avatar_card)
		var avatar_column := VBoxContainer.new()
		avatar_column.add_theme_constant_override("separation", 3)
		avatar_card.add_child(avatar_column)
		var portrait := TextureRect.new()
		portrait.texture = _avatar_region(index)
		portrait.modulate = Color.WHITE
		portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		portrait.custom_minimum_size = Vector2(72, 70)
		portrait.mouse_filter = Control.MOUSE_FILTER_IGNORE
		avatar_column.add_child(portrait)
		var avatar_button := Button.new()
		avatar_button.text = str(profile["name"])
		avatar_button.tooltip_text = "Use the %s appearance" % profile["name"]
		avatar_button.custom_minimum_size = Vector2(76, 30)
		avatar_button.toggle_mode = true
		avatar_button.button_group = avatar_group
		avatar_button.button_pressed = profile_id == _avatar_id
		avatar_button.add_theme_stylebox_override("normal", _style(Color("0b1b21"), Color("29474e"), 8))
		avatar_button.add_theme_stylebox_override("hover", _style(Color("143038"), Color(profile["tint"]), 8))
		avatar_button.add_theme_stylebox_override("pressed", _style(Color("17383d"), Color(profile["tint"]), 8))
		avatar_button.pressed.connect(func() -> void: _select_avatar(profile_id))
		avatar_column.add_child(avatar_button)
		_avatar_buttons[profile_id] = avatar_button
	_update_creator_toggle()
	var form := HFlowContainer.new()
	form.add_theme_constant_override("separation", 8)
	creator.add_child(form)
	_name_input = LineEdit.new()
	_name_input.placeholder_text = "Agent name"
	_name_input.text = "New Aitizen"
	_name_input.custom_minimum_size.x = 180
	form.add_child(_name_input)
	_x_input = _number_input(" X", 0, 4096, 32)
	_x_input.tooltip_text = "Preferred spawn X. The nearest free walkable tile is chosen automatically."
	form.add_child(_x_input)
	_y_input = _number_input(" Y", 0, 4096, 32)
	_y_input.tooltip_text = "Preferred spawn Y. Water and occupied tiles are avoided automatically."
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

	_search = LineEdit.new()
	_search.placeholder_text = "Search citizens by name or current action…"
	_search.text_changed.connect(func(_text: String) -> void: _rebuild_table())
	layout.add_child(_search)
	var body := HSplitContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(body)
	_table = Tree.new()
	_table.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_table.columns = 5
	_table.hide_root = true
	_table.column_titles_visible = true
	_table.select_mode = Tree.SELECT_ROW
	var columns := ["Citizen", "State", "Health", "Energy", "Current action"]
	for index: int in range(columns.size()):
		_table.set_column_title(index, columns[index])
	var widths := [150, 84, 62, 62, 132]
	for index: int in range(widths.size()):
		_table.set_column_custom_minimum_width(index, widths[index])
		_table.set_column_expand(index, index in [0, 4])
	_table.item_selected.connect(_inspect_selected)
	body.add_child(_table)
	var detail_column := VBoxContainer.new()
	detail_column.custom_minimum_size.x = 240
	body.add_child(detail_column)
	_details = RichTextLabel.new()
	_details.bbcode_enabled = false
	_details.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_details.text = "CITIZEN INSPECTOR\n\nSelect a citizen to see their needs, goal, inventory and decision reason."
	detail_column.add_child(_details)
	var memories := preload("res://scripts/ui/CitizenMemoryView.gd").new()
	add_child(memories)
	var memory_button := Button.new()
	memory_button.text = "Memory tree / Fear…"
	memory_button.pressed.connect(func() -> void:
		if not _selection.is_empty():
			memories.show_citizen(_selection))
	detail_column.add_child(memory_button)
	var focus := Button.new()
	focus.text = "Focus camera →"
	focus.pressed.connect(func() -> void:
		if not _selection.is_empty():
			focus_requested.emit(Vector2i(int(_selection.get("x", 0)), int(_selection.get("y", 0))))
			close_page()
	)
	detail_column.add_child(focus)
	var remove := Button.new()
	remove.text = "Deactivate selected citizen"
	remove.pressed.connect(func() -> void:
		if not _selection.is_empty() and "player" not in _selection.get("tags", []):
			remove_agent_requested.emit(str(_selection["id"]))
	)
	detail_column.add_child(remove)
	var footer := HBoxContainer.new()
	layout.add_child(footer)
	_status = Label.new()
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.text = "Waiting for agent registry…"
	_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	footer.add_child(_status)
	var refresh := Button.new()
	refresh.text = "REFRESH"
	refresh.pressed.connect(func() -> void: refresh_requested.emit())
	footer.add_child(refresh)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(self)


func _rebuild_table() -> void:
	_table.clear()
	var tree_root := _table.create_item()
	var query := _search.text.strip_edges().to_lower()
	var shown := 0
	for entity: Dictionary in _agents:
		var searchable := "%s %s" % [entity.get("name", ""), entity.get("action", "")]
		if not query.is_empty() and not searchable.to_lower().contains(query):
			continue
		var item := _table.create_item(tree_root)
		item.set_metadata(0, entity)
		var profile := _avatar_profile(str(entity.get("avatar_id", "scout")))
		item.set_text(0, "◆  %s" % str(entity.get("name", "Unknown")))
		item.set_custom_color(0, Color(str(profile.get("tint", "72d6bb"))))
		var metadata: Dictionary = entity.get("metadata", {}) if entity.get("metadata") is Dictionary else {}
		item.set_text(1, str(metadata.get("state", entity.get("goal", "idle"))).replace("_", " ").capitalize())
		var needs: Dictionary = entity.get("needs", {}) if entity.get("needs") is Dictionary else {}
		item.set_text(2, "%.0f%%" % float(needs["health"]) if needs.has("health") else "—")
		item.set_text(3, "%.0f%%" % float(needs["energy"]) if needs.has("energy") else "—")
		item.set_custom_color(2, Color("83c99c") if float(needs.get("health", 0)) >= 60 else Color("ee987c"))
		item.set_text(4, str(entity.get("action", "idle")).replace("_", " ").capitalize())
		if str(entity.get("id", "")) == str(_selection.get("id", "missing")):
			_selection = entity
			item.select(0)
		shown += 1
	_count.text = "%d / %d CITIZENS" % [shown, _agents.size()]


func _inspect_selected() -> void:
	var item := _table.get_selected()
	if item == null:
		return
	_selection = item.get_metadata(0)
	var profile := _avatar_profile(str(_selection.get("avatar_id", "scout")))
	var lines := PackedStringArray([str(_selection.get("name", "Citizen")), "Appearance: %s" % profile.get("name", "Aster"), "Position: %s, %s" % [_selection.get("x", 0), _selection.get("y", 0)], "", "CURRENT GOAL", str(_selection.get("goal", "idle")).replace("_", " "), "", "WHY THIS ACTION", str(_selection.get("decision_reason", "No decision explanation reported.")), "", "NEEDS"])
	var needs: Dictionary = _selection.get("needs", {}) if _selection.get("needs") is Dictionary else {}
	for key: String in ["health", "hunger", "thirst", "energy"]:
		lines.append("%s: %s" % [key.capitalize(), str(needs.get(key, "Unknown"))])
	lines.append("\nINVENTORY\n%s" % str(_selection.get("inventory", {})))
	var trace: Array = _selection.get("decision_trace", [])
	if not trace.is_empty():
		lines.append("\nDECISION CHECKS")
		for candidate: Dictionary in trace:
			lines.append("%s · %.2f · %s" % [str(candidate.get("goal", "")).replace("_", " "), float(candidate.get("score", 0)), "Chosen" if candidate.get("selected", false) else str(candidate.get("blocked_by", "Unavailable"))])
	_details.text = "\n".join(lines)
	var metadata: Dictionary = _selection.get("metadata", {})
	var recent: Array = metadata.get("recent_actions", [])
	if not recent.is_empty():
		_details.text += "\n\nRECENT ACTIONS"
		for action: Dictionary in recent:
			_details.text += "\nT%s · %s · %s\n%s" % [action.get("tick", 0), action.get("action", ""), action.get("outcome", ""), action.get("failure", "") if action.get("failure") != null else str(action.get("result", {}))]


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
	mode.text = "%s  ·  (%d, %d)  ·  VISION %d" % [
		"AUTONOMOUS" if "autonomous" in tags else "MANUAL",
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
		_autonomous_input.button_pressed,
		_avatar_id
	)
	_status.text = "Creating %s with the %s appearance…" % [agent_name, _avatar_profile(_avatar_id).get("name", "Aster")]
	_creator_content.hide()
	_update_creator_toggle()


func _select_avatar(profile_id: String) -> void:
	_avatar_id = profile_id
	for key: String in _avatar_buttons:
		(_avatar_buttons[key] as Button).button_pressed = key == profile_id
	_update_creator_toggle()


func _toggle_creator() -> void:
	_creator_content.visible = not _creator_content.visible
	_update_creator_toggle()


func _update_creator_toggle() -> void:
	if _creator_toggle == null:
		return
	var marker := "−" if _creator_content != null and _creator_content.visible else "＋"
	_creator_toggle.text = "%s  CREATE A CITIZEN  ·  %s APPEARANCE" % [marker, str(_avatar_profile(_avatar_id).get("name", "Aster")).to_upper()]


func _avatar_index(profile_id: String) -> int:
	for index: int in range(CITIZEN_AVATARS.size()):
		if str(CITIZEN_AVATARS[index]["id"]) == profile_id:
			return index
	return 0


func _avatar_profile(profile_id: String) -> Dictionary:
	return CITIZEN_AVATARS[_avatar_index(profile_id)]


func _avatar_region(index: int) -> AtlasTexture:
	return preload("res://scripts/world/CitizenVisuals.gd").portrait(str(CITIZEN_AVATARS[index]["id"]))


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
