# CraftingPanel.gd
extends Control
class_name CraftingPanel

## Presents agent capabilities as a polished, backend-driven blueprint library.

signal refresh_requested()

@onready var panel: PanelContainer = $Panel
@onready var edge_button: Button = $EdgeButton
@onready var cards: VBoxContainer = $Panel/Margin/Layout/BlueprintScroll/BlueprintCards
@onready var status_label: Label = $Panel/Margin/Layout/Status
@onready var count_label: Label = $Panel/Margin/Layout/Header/Count
@onready var all_button: Button = $Panel/Margin/Layout/Tabs/All
@onready var build_button: Button = $Panel/Margin/Layout/Tabs/Build
@onready var craft_button: Button = $Panel/Margin/Layout/Tabs/Craft

var _is_open := false
var _drawer_tween: Tween
var _blueprints: Dictionary = {}
var _active_filter := "all"


func _ready() -> void:
	edge_button.pressed.connect(_toggle_panel)
	all_button.pressed.connect(func() -> void: _set_filter("all"))
	build_button.pressed.connect(func() -> void: _set_filter("build"))
	craft_button.pressed.connect(func() -> void: _set_filter("craft"))
	craft_button.disabled = false
	$Panel/Margin/Layout/Refresh.pressed.connect(func() -> void: refresh_requested.emit())
	panel.modulate.a = 0.0
	panel.offset_left = 20.0
	panel.offset_right = 390.0
	panel.hide()
	edge_button.text = "‹"
	edge_button.offset_left = -56.0
	edge_button.offset_right = -20.0
	get_viewport().size_changed.connect(_layout_drawer)
	_layout_drawer()


func _layout_drawer() -> void:
	panel.offset_top = 88.0
	panel.offset_bottom = -96.0
	$Panel/Margin/Layout/Description.hide()
	$Panel/Margin/Layout/BlueprintScroll.custom_minimum_size.y = 160


func display_blueprints(blueprints: Dictionary) -> void:
	_blueprints = blueprints.duplicate(true)
	_render_blueprints()


func _render_blueprints() -> void:
	for child: Node in cards.get_children():
		child.queue_free()
	var names: Array[String] = []
	for blueprint_name: Variant in _blueprints.keys():
		var blueprint: Dictionary = _blueprints[blueprint_name]
		var category := str(blueprint.get("category", "build"))
		if _active_filter == "all" or category == _active_filter:
			names.append(str(blueprint_name))
	names.sort()
	for blueprint_name: String in names:
		var card: PanelContainer = _add_blueprint_card(blueprint_name, _blueprints[blueprint_name])
		_animate_card(card, names.find(blueprint_name))
	count_label.text = "%d KNOWN" % names.size()
	status_label.text = "Blueprint knowledge synchronized"
	status_label.modulate = Color("75d7ba")


func _set_filter(filter_name: String) -> void:
	_active_filter = filter_name
	all_button.flat = filter_name != "all"
	build_button.flat = filter_name != "build"
	craft_button.flat = filter_name != "craft"
	_render_blueprints()


func display_error(error_message: String) -> void:
	status_label.text = error_message
	status_label.modulate = Color("ef8f78")


func _add_blueprint_card(blueprint_name: String, blueprint: Dictionary) -> PanelContainer:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(318, 112)
	var card_style := StyleBoxFlat.new()
	card_style.bg_color = Color("18242b")
	card_style.border_width_left = 3
	card_style.border_color = _blueprint_color(blueprint_name)
	card_style.corner_radius_top_left = 6
	card_style.corner_radius_top_right = 6
	card_style.corner_radius_bottom_right = 6
	card_style.corner_radius_bottom_left = 6
	card_style.content_margin_left = 13.0
	card_style.content_margin_top = 10.0
	card_style.content_margin_right = 13.0
	card_style.content_margin_bottom = 10.0
	card.add_theme_stylebox_override("panel", card_style)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	card.add_child(row)
	var icon := TextureRect.new()
	icon.custom_minimum_size = Vector2(88, 88)
	icon.texture = load(_blueprint_image_path(blueprint_name)) as Texture2D
	var world_regions := {"fence": Rect2(329, 662, 307, 153), "workbench": Rect2(966, 625, 269, 213), "storage": Rect2(639, 610, 309, 230)}
	if world_regions.has(blueprint_name):
		var texture := AtlasTexture.new()
		texture.atlas = load("res://assets/pixel_art/aitizen_realm_atlas_v1_clean.png") as Texture2D
		texture.region = world_regions[blueprint_name]
		icon.texture = texture
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(icon)

	var details := VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 3)
	row.add_child(details)
	var title := Label.new()
	title.text = blueprint_name.replace("_", " ").to_upper()
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color("f3e7ce"))
	details.add_child(title)
	var materials: Dictionary = blueprint.get("materials", {})
	var cost_parts: Array[String] = []
	for material_key: Variant in materials:
		cost_parts.append(
			"%s %.0f" % [str(material_key).capitalize(), float(materials[material_key])]
		)
	var cost := Label.new()
	cost.text = "  •  ".join(cost_parts)
	cost.add_theme_color_override("font_color", Color("aebdc2"))
	cost.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(cost)
	var work := Label.new()
	work.text = "%.0f work  ·  RECIPE KNOWN" % float(blueprint.get("work_required", 0.0))
	work.add_theme_color_override("font_color", Color("75d7ba"))
	work.add_theme_font_size_override("font_size", 12)
	details.add_child(work)
	cards.add_child(card)
	return card


func toggle_panel() -> void:
	_is_open = not _is_open
	edge_button.text = "›" if _is_open else "‹"
	if _drawer_tween != null and _drawer_tween.is_valid():
		_drawer_tween.kill()
	_drawer_tween = create_tween().set_parallel(true)
	_drawer_tween.set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	if _is_open:
		panel.show()
		_drawer_tween.tween_property(panel, "offset_left", -390.0, 0.34)
		_drawer_tween.tween_property(panel, "offset_right", -20.0, 0.34)
		_drawer_tween.tween_property(panel, "modulate:a", 1.0, 0.22)
		_drawer_tween.tween_property(edge_button, "offset_left", -426.0, 0.34)
		_drawer_tween.tween_property(edge_button, "offset_right", -390.0, 0.34)
	else:
		_drawer_tween.tween_property(panel, "offset_left", 20.0, 0.30)
		_drawer_tween.tween_property(panel, "offset_right", 390.0, 0.30)
		_drawer_tween.tween_property(panel, "modulate:a", 0.0, 0.20)
		_drawer_tween.tween_property(edge_button, "offset_left", -56.0, 0.30)
		_drawer_tween.tween_property(edge_button, "offset_right", -20.0, 0.30)
		_drawer_tween.chain().tween_callback(panel.hide)


func open_panel() -> void:
	if not _is_open:
		toggle_panel()


func close_panel() -> void:
	if _is_open:
		toggle_panel()


func _toggle_panel() -> void:
	toggle_panel()


func _animate_open() -> void:
	_drawer_tween = create_tween().set_parallel(true)
	_drawer_tween.set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	_drawer_tween.tween_property(panel, "offset_left", -390.0, 0.42)
	_drawer_tween.tween_property(panel, "offset_right", -20.0, 0.42)
	_drawer_tween.tween_property(panel, "modulate:a", 1.0, 0.28)


func _animate_card(card: PanelContainer, index: int) -> void:
	card.modulate.a = 0.0
	card.scale = Vector2(0.96, 0.96)
	card.pivot_offset = card.custom_minimum_size * 0.5
	var delay: float = float(index) * 0.07
	var reveal := create_tween().set_parallel(true)
	reveal.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	reveal.tween_property(card, "modulate:a", 1.0, 0.24).set_delay(delay)
	reveal.tween_property(card, "scale", Vector2.ONE, 0.28).set_delay(delay)


func _blueprint_image_path(blueprint_name: String) -> String:
	match blueprint_name:
		"campfire", "torch": return "res://assets/ui/blueprints/campfire.png"
		"storage", "workbench", "well": return "res://assets/ui/blueprints/storage.png"
		_: return "res://assets/ui/blueprints/shelter.png"


func _blueprint_color(blueprint_name: String) -> Color:
	match blueprint_name:
		"campfire", "torch": return Color("ef9b4d")
		"storage", "workbench", "well": return Color("d7bb78")
		"tent": return Color("d89972")
		"fence": return Color("a87b53")
		_: return Color("68c7b1")
