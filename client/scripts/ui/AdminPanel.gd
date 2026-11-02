extends Control
class_name AdminPanel

## Full agent administration page built from live backend entity records.

signal create_agent_requested(name: String, x: int, y: int, radius: int, autonomous: bool, avatar_id: String, gender: String, diet: String)
signal remove_agent_requested(entity_id: String)
signal refresh_requested()
signal focus_requested(position: Vector2i)
signal dive_requested(entity_id: String)
signal ai_mode_requested(entity_id: String, mode: String)
signal gift_requested(entity_id: String, recipient: String, item: String, amount: float)
signal cave_requested(entity_id: String)
signal dive_return_requested(entity_id: String)
signal boat_requested(entity_id: String, command: String, destination: Vector2i)
signal follow_entity_requested(entity_id: String)

const CITIZEN_AVATARS: Array[Dictionary] = [
	{"id": "juniper", "name": "Juniper", "tint": "449b8c"},
	{"id": "rowan", "name": "Rowan (new)", "tint": "448d91"},
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
var _gender_input: OptionButton
var _diet_input: OptionButton
var _status: Label
var _count: Label
var _table: Tree
var _search: LineEdit
var _details: RichTextLabel
var _profile_page: PanelContainer
var _profile_name: Label
var _profile_identity: Label
var _profile_portrait: TextureRect
var _profile_bars: Dictionary = {}
var _chat: AcceptDialog
var _chat_messages: VBoxContainer
var _chat_heading: Label
var _chat_scroll: ScrollContainer
var _chat_signature := ""
var _chat_threads: OptionButton
var _chat_peer := ""
var _chat_seen: Dictionary = {}
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
	_profile_page.hide()
	hide()


func display_agents(entities: Array) -> void:
	_agents = entities.filter(func(value: Variant) -> bool:
		return value is Dictionary and str(value.get("kind", "agent")).to_lower() == "agent"
	)
	_table.set_block_signals(true)
	_rebuild_table()
	_table.set_block_signals(false)
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
	_gender_input = OptionButton.new()
	for gender: String in ["unspecified", "female", "male", "nonbinary"]:
		_gender_input.add_item(gender.capitalize())
	_gender_input.tooltip_text = "Gender is independent of appearance, skills and work."
	form.add_child(_gender_input)
	_diet_input = OptionButton.new()
	for diet: String in ["omnivore", "vegetarian"]:
		_diet_input.add_item(diet.capitalize())
	form.add_child(_diet_input)
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
	_table.columns = 6
	_table.hide_root = true
	_table.column_titles_visible = true
	_table.select_mode = Tree.SELECT_ROW
	var columns := ["Citizen", "State", "Health", "Energy", "Current action", "AI mode"]
	for index: int in range(columns.size()):
		_table.set_column_title(index, columns[index])
	var widths := [130, 70, 58, 58, 100, 100]
	for index: int in range(widths.size()):
		_table.set_column_custom_minimum_width(index, widths[index])
		_table.set_column_expand(index, index in [0, 4])
	_table.item_selected.connect(func() -> void:
		_inspect_selected()
		_profile_page.show())
	body.add_child(_table)
	var detail_column := VBoxContainer.new()
	detail_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var detail_scroll := ScrollContainer.new()
	detail_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	detail_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_build_profile_shell(detail_scroll)
	detail_scroll.add_child(detail_column)
	var profile_tabs := TabContainer.new()
	profile_tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	profile_tabs.custom_minimum_size.y = 400
	profile_tabs.add_theme_stylebox_override("panel", _style(Color("0d2327"), Color("294b4f"), 8))
	profile_tabs.add_theme_stylebox_override("tab_selected", _style(Color("23564c"), Color("70cbb1"), 6))
	profile_tabs.add_theme_stylebox_override("tab_unselected", _style(Color("102c30"), Color("294b4f"), 6))
	detail_column.add_child(profile_tabs)
	var overview := VBoxContainer.new()
	overview.name = "Life & decisions"
	profile_tabs.add_child(overview)
	var commands := VBoxContainer.new()
	commands.name = "Actions & communication"
	profile_tabs.add_child(commands)
	detail_column = commands
	_details = RichTextLabel.new()
	_details.bbcode_enabled = false
	_details.fit_content = false
	_details.scroll_active = true
	_details.custom_minimum_size.y = 340
	_details.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_details.text = "CITIZEN INSPECTOR\n\nSelect a citizen to see their needs, goal, inventory and decision reason."
	overview.add_child(_details)
	var direct_chat := preload("res://scripts/ui/CitizenDirectChat.gd").new()
	add_child(direct_chat)
	var talk := Button.new()
	talk.text = "Talk to this citizen…"
	detail_column.add_child(talk)
	talk.pressed.connect(func() -> void: direct_chat.open_citizen(_selection))
	_chat = AcceptDialog.new()
	_chat.title = "Citizen conversations · English"
	add_child(_chat)
	var chat_layout := VBoxContainer.new()
	chat_layout.custom_minimum_size = Vector2(560, 360)
	chat_layout.add_theme_constant_override("separation", 12)
	_chat.add_child(chat_layout)
	_chat_heading = Label.new()
	_chat_heading.add_theme_color_override("font_color", Color("72d6bb"))
	chat_layout.add_child(_chat_heading)
	_chat_threads = OptionButton.new()
	chat_layout.add_child(_chat_threads)
	_chat_threads.item_selected.connect(func(index: int) -> void:
		_chat_peer = str(_chat_threads.get_item_metadata(index))
		_chat_signature = ""
		_update_conversation_text())
	_chat_scroll = ScrollContainer.new()
	_chat_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_chat_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	chat_layout.add_child(_chat_scroll)
	_chat_messages = VBoxContainer.new()
	_chat_messages.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_chat_messages.add_theme_constant_override("separation", 10)
	_chat_scroll.add_child(_chat_messages)
	var chat_note := Label.new()
	chat_note.text = "LIVE CONVERSATIONS · Observed speech, not player messages"
	chat_note.add_theme_font_size_override("font_size", 12)
	chat_layout.add_child(chat_note)
	var chat_button := Button.new()
	chat_button.text = "Open conversations / share supplies"
	chat_button.pressed.connect(_open_conversations)
	detail_column.add_child(chat_button)
	var recipient_input := OptionButton.new()
	var item_input := LineEdit.new()
	item_input.placeholder_text = "Resource ID: food, wood, stone…"
	var quantity := SpinBox.new()
	quantity.min_value = 1
	quantity.max_value = 50
	var give_button := Button.new()
	give_button.text = "Give supplies (stand beside recipient)"
	chat_button.pressed.connect(func() -> void:
		recipient_input.clear()
		for citizen: Dictionary in _agents:
			if citizen.get("id") != _selection.get("id"):
				recipient_input.add_item(str(citizen.get("name", "Citizen")))
				recipient_input.set_item_metadata(recipient_input.item_count-1, citizen.id))
	give_button.pressed.connect(func() -> void:
		if not _selection.is_empty() and recipient_input.selected >= 0:
			gift_requested.emit(str(_selection.id), str(recipient_input.get_item_metadata(recipient_input.selected)), item_input.text.strip_edges(), quantity.value))
	for control: Control in [recipient_input, item_input, quantity, give_button]:
		detail_column.add_child(control)
	var memories := preload("res://scripts/ui/CitizenMemoryView.gd").new()
	add_child(memories)
	var memory_button := Button.new()
	memory_button.text = "Memory tree / Fear…"
	memory_button.pressed.connect(func() -> void:
		if not _selection.is_empty():
			memories.show_citizen(_selection))
	detail_column.add_child(memory_button)
	var family_view := preload("res://scripts/ui/FamilyTreeView.gd").new()
	add_child(family_view)
	var family_button := Button.new()
	family_button.text = "Family tree…"
	family_button.pressed.connect(func() -> void:
		if not _selection.is_empty():
			family_view.show_family(_selection, _agents))
	detail_column.add_child(family_button)
	var dive := Button.new()
	dive.text = "Dive from shore / anchored boat"
	dive.tooltip_text = "Requires nearby known shallow water, 70 energy and 60 health. Automatically returns to shore."
	dive.pressed.connect(func() -> void:
		if not _selection.is_empty():
			dive_requested.emit(str(_selection.get("id", ""))))
	detail_column.add_child(dive)
	for ai_mode: String in ["utility", "local_llm"]:
		var ai_button := Button.new()
		ai_button.text = "Use Utility AI" if ai_mode == "utility" else "Use Local LLM + fallback"
		ai_button.tooltip_text = "Changes this citizen's next decision. Local LLM citizens share a bounded queue; Utility AI stays active while waiting."
		ai_button.pressed.connect(func() -> void:
			if not _selection.is_empty():
				ai_mode_requested.emit(str(_selection.get("id", "")), ai_mode))
		detail_column.add_child(ai_button)
	var cave_button := Button.new()
	cave_button.text = "Explore adjacent cave"
	cave_button.tooltip_text = "Healthy citizens also explore known caves and water autonomously when their needs are met."
	cave_button.pressed.connect(func() -> void:
		if not _selection.is_empty():
			cave_requested.emit(str(_selection.get("id", ""))))
	detail_column.add_child(cave_button)
	var return_button := Button.new()
	return_button.text = "Return diver to safety"
	return_button.tooltip_text = "Retrace the selected citizen's dive route to shore."
	return_button.pressed.connect(func() -> void:
		if not _selection.is_empty():
			dive_return_requested.emit(str(_selection.get("id", ""))))
	detail_column.add_child(return_button)
	var boat_commands := OptionButton.new()
	for caption: String in ["Build boat (20 wood, 8 fiber)", "Launch crafted boat", "Board boat", "Row to coordinates", "Anchor boat", "Store dive cargo", "Disembark to shore", "Unload cargo"]:
		boat_commands.add_item(caption)
	detail_column.add_child(boat_commands)
	var destination_row := HBoxContainer.new()
	var boat_x := SpinBox.new()
	var boat_y := SpinBox.new()
	for input: SpinBox in [boat_x, boat_y]:
		input.max_value = 4096
		input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		destination_row.add_child(input)
	boat_x.prefix = "X"
	boat_y.prefix = "Y"
	detail_column.add_child(destination_row)
	var boat_action := Button.new()
	boat_action.text = "Apply boat command"
	boat_action.pressed.connect(func() -> void:
		if not _selection.is_empty():
			var command: String = ["craft", "launch", "board", "row", "anchor", "store", "disembark", "unload"][boat_commands.selected]
			boat_requested.emit(str(_selection.get("id", "")), command, Vector2i(int(boat_x.value), int(boat_y.value))))
	detail_column.add_child(boat_action)
	var focus := Button.new()
	focus.text = "Follow citizen / diver →"
	focus.pressed.connect(func() -> void:
		if not _selection.is_empty():
			follow_entity_requested.emit(str(_selection.get("id", "")))
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
		var unread := 0
		for message: Dictionary in entity.get("metadata", {}).get("conversation", []):
			if not _chat_seen.has(str(entity.get("id", "")) + ":" + str(message.get("id", str(message)))):
				unread += 1
		item.set_text(0, "◆  %s%s" % [str(entity.get("name", "Unknown")), "  · %d new" % unread if unread > 0 else ""])
		item.set_custom_color(0, Color(str(profile.get("tint", "72d6bb"))))
		var metadata: Dictionary = entity.get("metadata", {}) if entity.get("metadata") is Dictionary else {}
		item.set_text(1, str(metadata.get("state", entity.get("goal", "idle"))).replace("_", " ").capitalize())
		var needs: Dictionary = entity.get("needs", {}) if entity.get("needs") is Dictionary else {}
		item.set_text(2, "%.0f%%" % float(needs["health"]) if needs.has("health") else "—")
		item.set_text(3, "%.0f%%" % float(needs["energy"]) if needs.has("energy") else "—")
		item.set_custom_color(2, Color("83c99c") if float(needs.get("health", 0)) >= 60 else Color("ee987c"))
		item.set_text(4, str(entity.get("action", "idle")).replace("_", " ").capitalize())
		item.set_text(5, _ai_label(entity))
		item.set_tooltip_text(5, "Local LLM uses Utility AI while thinking or when unavailable. Change mode in the inspector.")
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
	_update_profile_header()
	var profile := _avatar_profile(str(_selection.get("avatar_id", "scout")))
	var lines := PackedStringArray(["Appearance: %s" % profile.get("name", "Aster"), "Position: %s, %s" % [_selection.get("x", 0), _selection.get("y", 0)], "", "CURRENT GOAL", str(_selection.get("goal", "idle")).replace("_", " ").capitalize(), "", "WHY THIS ACTION", str(_selection.get("decision_reason", "No decision explanation reported."))])
	lines.append("\nCARRIED SUPPLIES")
	var inventory: Dictionary = _selection.get("inventory", {})
	var supplies: Dictionary = inventory.get("items", {})
	if supplies.is_empty():
		lines.append("Pack empty")
	for material_key: String in supplies:
		lines.append("• %s   × %s" % [material_key.replace("_", " ").capitalize(), str(supplies[material_key])])
	lines.append("\nEXPEDITION\nOxygen: %s%% · Depth: %sm\nPhase: %s\nReturn: %s\nDiscovered sites: %d" % [str(_selection.get("oxygen", 100)), str(_selection.get("depth", 0)), str(_selection.get("dive_phase", "none")), str(_selection.get("dive_origin", [])), _selection.get("marine_discoveries", {}).size()])
	if _selection.get("boat") is Dictionary:
		lines.append("Boat / cargo: %s" % str(_selection.boat))
	var trace: Array = _selection.get("decision_trace", [])
	if not trace.is_empty():
		lines.append("\nDECISION CHECKS")
		for candidate: Dictionary in trace:
			lines.append("%s · %.2f · %s" % [str(candidate.get("goal", "")).replace("_", " "), float(candidate.get("score", 0)), "Chosen" if candidate.get("selected", false) else str(candidate.get("blocked_by", "Unavailable"))])
	_details.text = "\n".join(lines)
	var metadata: Dictionary = _selection.get("metadata", {})
	_details.text += "\n\nFAMILY & LIFE\nStage: %s · Age: %.1f years\nPartner: %s\nParents: %s\nGuardian: %s\n%s" % [metadata.get("life_stage", "adult"), float(metadata.get("age_days", 6570)) / 365.0, str(metadata.get("partner_id", "None")), str(metadata.get("parent_ids", [])), str(metadata.get("guardian_id", "Independent")), str(metadata.get("care_status", ""))]
	if metadata.get("pregnancy") is Dictionary:
		_details.text += "\nExpecting a child · %.0f biological days remaining" % maxf(0, float(metadata.pregnancy.get("due_age_days", 0)) - float(metadata.get("age_days", 0)))
	var prenatal: Dictionary = _selection.get("pregnancy_status", {})
	if prenatal.get("phase", "none") in ["pregnant", "birth_due"]:
		_details.text += "\nPregnancy: %.0f%% · Trimester %d\n%s\nLight duties; food, water and a safe home are priorities." % [float(prenatal.get("progress", 0)) * 100, int(prenatal.get("trimester", 1)), ", ".join(prenatal.get("warnings", []))]
	elif prenatal.get("phase", "none") == "recovering":
		_details.text += "\nPost-birth recovery: %.0f biological days remaining · Light duties" % float(prenatal.get("recovery_days", 0))
	var ambition: Dictionary = metadata.get("ambition", {})
	if not ambition.is_empty():
		_details.text += "\n\nPERSONAL AMBITION\n%s\n%s / %s · %s" % [ambition.get("title", ""), ambition.get("progress", 0), ambition.get("target", 0), ambition.get("status", "active")]
	_details.text += "\n\nLEARNING / EVIDENCE\nRemembered danger locations: %d\nLast actual outcome: %s" % [metadata.get("learned_dangers", {}).size(), str(metadata.get("last_learned_outcome", "No completed actions yet"))]
	var verified_report: Dictionary = metadata.get("last_verified_report", {})
	if not verified_report.is_empty():
		_details.text += "\nVerified advice: %s · tick %s" % [verified_report.get("outcome", ""), verified_report.get("verified_tick", 0)]
	_update_conversation_text()
	_details.text += "\nAI MODE\n%s\n%s" % [_ai_label(_selection), str(metadata.get("llm_planner", {}).get("status", ""))]
	_details.text += "\nIDENTITY\nGender: %s\nDiet: %s" % [_selection.get("gender", "unspecified"), _selection.get("diet", "omnivore")]
	_details.text += "\n\nCOMMUNITY\n%s" % str(metadata.get("community_task", metadata.get("last_community_task", "No social commitment")))
	for bond: Dictionary in _selection.get("relationships", []):
		_details.text += "\n%s · %s · trust %.0f%%" % [bond.get("name", "Citizen"), bond.get("label", "Acquaintance"), float(bond.get("trust", 0)) * 100]
	var recent: Array = metadata.get("recent_actions", [])
	if not recent.is_empty():
		_details.text += "\n\nRECENT ACTIONS"
		for action: Dictionary in recent:
			_details.text += "\nT%s · %s · %s\n%s" % [action.get("tick", 0), action.get("action", ""), action.get("outcome", ""), action.get("failure", "") if action.get("failure") != null else str(action.get("result", {}))]


func _build_profile_shell(detail_scroll: ScrollContainer) -> void:
	_profile_page = PanelContainer.new()
	_profile_page.set_anchors_preset(Control.PRESET_FULL_RECT)
	_profile_page.offset_left = 18
	_profile_page.offset_top = 76
	_profile_page.offset_right = -18
	_profile_page.offset_bottom = -18
	_profile_page.add_theme_stylebox_override("panel", _style(Color("0a1c20"), Color("4e8b81"), 14))
	add_child(_profile_page)
	var margin := MarginContainer.new()
	for side in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	_profile_page.add_child(margin)
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 18)
	margin.add_child(layout)
	var header := HBoxContainer.new()
	layout.add_child(header)
	_profile_name = Label.new()
	_profile_name.add_theme_font_size_override("font_size", 28)
	_profile_name.add_theme_color_override("font_color", Color("efdfb8"))
	_profile_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_profile_name)
	var back := Button.new()
	back.text = "← All citizens"
	back.pressed.connect(func() -> void: _profile_page.hide())
	header.add_child(back)
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 28)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(body)
	var identity := VBoxContainer.new()
	identity.custom_minimum_size.x = 220
	identity.add_theme_constant_override("separation", 5)
	var identity_scroll := ScrollContainer.new()
	identity_scroll.custom_minimum_size.x = 240
	identity_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(identity_scroll)
	identity_scroll.add_child(identity)
	_profile_portrait = TextureRect.new()
	_profile_portrait.custom_minimum_size = Vector2(160, 110)
	_profile_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_profile_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	identity.add_child(_profile_portrait)
	_profile_identity = Label.new()
	_profile_identity.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_profile_identity.add_theme_color_override("font_color", Color("87cbbb"))
	identity.add_child(_profile_identity)
	for key in ["health", "energy", "hunger", "thirst"]:
		var label := Label.new()
		identity.add_child(label)
		var bar := ProgressBar.new()
		bar.custom_minimum_size.y = 12
		bar.show_percentage = false
		bar.add_theme_stylebox_override("background", _style(Color("182f35"), Color("182f35"), 5))
		identity.add_child(bar)
		_profile_bars[key] = {"bar": bar, "label": label}
	body.add_child(detail_scroll)
	_profile_page.hide()


func _update_profile_header() -> void:
	_profile_name.text = str(_selection.get("name", "Citizen"))
	_profile_portrait.texture = preload("res://scripts/world/CitizenVisuals.gd").portrait(str(_selection.get("visual_avatar", _selection.get("avatar_id", "scout"))))
	# A bust portrait reads better than a miniature full-body game sprite.
	if _profile_portrait.texture is AtlasTexture:
		var portrait := _profile_portrait.texture as AtlasTexture
		portrait.region.size.y *= 0.52
	_profile_identity.text = "%s · %s\n%s\n%s" % [str(_selection.get("gender", "unspecified")).capitalize(), str(_selection.get("diet", "omnivore")).capitalize(), _ai_label(_selection), str(_selection.get("action", "idle")).replace("_", " ").capitalize()]
	var needs: Dictionary = _selection.get("needs", {}) if _selection.get("needs") is Dictionary else {}
	for key: String in _profile_bars:
		var widgets: Dictionary = _profile_bars[key]
		var value: float = clampf(float(needs.get(key, 0)), 0, 100)
		widgets.label.text = "%s   %s" % [key.capitalize(), "%.0f / 100" % value if needs.has(key) else "Not reported"]
		widgets.bar.value = value
		widgets.bar.tooltip_text = "Higher means greater need" if key in ["hunger", "thirst"] else "Higher is better"
		var warning: bool = value > 65 if key in ["hunger", "thirst"] else value < 35
		var color := Color("ee8c73") if warning else Color("70cbb1")
		widgets.bar.add_theme_stylebox_override("fill", _style(color, color, 5))


func _open_conversations() -> void:
	_chat.popup_centered(Vector2i(620, 440))
	_chat_signature = ""
	_update_conversation_text()

func _update_conversation_text() -> void:
	var entries: Array = _selection.get("metadata", {}).get("conversation", [])
	var signature := str([_selection.get("id", ""), entries, _chat_peer])
	if signature == _chat_signature:
		return
	_chat_signature = signature
	_chat_heading.text = "%s · Conversations" % _selection.get("name", "Select a citizen")
	var peers: Dictionary = {}
	for entry: Dictionary in entries:
		var peer := _conversation_peer(entry)
		peers[peer] = entry.get("recipient", "Citizen") if _outgoing(entry) else entry.get("sender", "Citizen")
	_chat_threads.clear()
	_chat_threads.add_item("All conversations")
	_chat_threads.set_item_metadata(0, "")
	if not _chat_peer.is_empty() and not peers.has(_chat_peer):
		_chat_peer = ""
	for peer: String in peers:
		var unread := 0
		for entry: Dictionary in entries:
			if _conversation_peer(entry) == peer and not _chat_seen.has(str(_selection.get("id", "")) + ":" + str(entry.get("id", str(entry)))):
				unread += 1
		_chat_threads.add_item(str(peers[peer]) + (" · %d new" % unread if unread > 0 else ""))
		_chat_threads.set_item_metadata(_chat_threads.item_count - 1, peer)
		if peer == _chat_peer:
			_chat_threads.select(_chat_threads.item_count - 1)
	for child: Node in _chat_messages.get_children():
		_chat_messages.remove_child(child)
		child.queue_free()
	if entries.is_empty():
		var empty := Label.new()
		empty.text = "No messages yet. Nearby awake citizens can talk and share supplies."
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_chat_messages.add_child(empty)
	for entry: Dictionary in entries:
		if not _chat_peer.is_empty() and _conversation_peer(entry) != _chat_peer:
			continue
		if _chat.visible:
			_chat_seen[str(_selection.get("id", "")) + ":" + str(entry.get("id", str(entry)))] = true
		var outgoing := _outgoing(entry)
		var row := HBoxContainer.new()
		_chat_messages.add_child(row)
		var spacer := Control.new()
		spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if outgoing:
			row.add_child(spacer)
		var bubble := PanelContainer.new()
		bubble.custom_minimum_size.x = 390
		bubble.add_theme_stylebox_override("panel", _style(Color("17483e") if outgoing else Color("182b32"), Color("31554f"), 12))
		row.add_child(bubble)
		if not outgoing:
			row.add_child(spacer)
		var contents := VBoxContainer.new()
		bubble.add_child(contents)
		var sender := Button.new()
		sender.flat = true
		sender.alignment = HORIZONTAL_ALIGNMENT_LEFT
		sender.text = "%s → %s" % [entry.get("sender", "Citizen"), entry.get("recipient", "Citizen")]
		sender.tooltip_text = "Focus the speaker in the world"
		sender.pressed.connect(func() -> void:
			for citizen: Dictionary in _agents:
				if str(citizen.get("id", "")) == str(entry.get("sender_id", "missing")) or (not entry.has("sender_id") and citizen.get("name") == entry.get("sender")):
					_chat.hide()
					close_page()
					focus_requested.emit(Vector2i(int(citizen.get("x", 0)), int(citizen.get("y", 0))))
					break)
		sender.add_theme_color_override("font_color", Color("83ddbe"))
		sender.add_theme_font_size_override("font_size", 12)
		contents.add_child(sender)
		var message := Label.new()
		message.text = str(entry.get("content", ""))
		message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		contents.add_child(message)
		var stamp := Label.new()
		stamp.text = "%s · Tick %d" % ["Local LLM" if entry.get("origin", "simulation") == "local_llm" else "Simulation", int(entry.get("tick", 0))]
		stamp.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		stamp.add_theme_font_size_override("font_size", 11)
		contents.add_child(stamp)
	_scroll_chat_to_bottom.call_deferred()
	while _chat_seen.size() > 4000:
		_chat_seen.erase(_chat_seen.keys()[0])

func _scroll_chat_to_bottom() -> void:
	await get_tree().process_frame
	_chat_scroll.scroll_vertical = int(_chat_scroll.get_v_scroll_bar().max_value)

func _outgoing(entry: Dictionary) -> bool:
	return str(entry.sender_id) == str(_selection.get("id", "")) if entry.has("sender_id") else str(entry.get("sender", "")) == str(_selection.get("name", ""))

func _conversation_peer(entry: Dictionary) -> String:
	return str(entry.get("recipient_id", entry.get("recipient", ""))) if _outgoing(entry) else str(entry.get("sender_id", entry.get("sender", "")))

func _ai_label(entity: Dictionary) -> String:
	var mode := str(entity.get("ai_mode", entity.get("metadata", {}).get("ai_mode", "unknown")))
	return "Local LLM" if mode == "local_llm" else "Utility AI" if mode == "utility" else "Not reported"

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
		_avatar_id,
		_gender_input.get_item_text(_gender_input.selected).to_lower(),
		_diet_input.get_item_text(_diet_input.selected).to_lower()
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
