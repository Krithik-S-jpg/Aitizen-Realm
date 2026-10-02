# TileInspector.gd
extends Control
class_name TileInspector

## Floating UI inspector overlay showing metrics of clicked grid cells.

@onready var panel: PanelContainer = $PanelContainer
@onready var label_title: Label = $PanelContainer/VBoxContainer/Title
@onready var label_pos: Label = $PanelContainer/VBoxContainer/Position
@onready var label_chunk: Label = $PanelContainer/VBoxContainer/Chunk
@onready var label_terrain: Label = $PanelContainer/VBoxContainer/Terrain
@onready var label_id: Label = $PanelContainer/VBoxContainer/TileID
@onready var label_quantity: Label = $PanelContainer/VBoxContainer/Quantity
@onready var close_button: Button = $PanelContainer/VBoxContainer/CloseButton
var _selected_entity_id := ""
var _selected_structure_id := ""
var _entry_tween: Tween

func _ready() -> void:
	panel.hide()
	close_button.pressed.connect(_on_close_button_pressed)
	var style := StyleBoxFlat.new()
	style.bg_color = Color("17221ff5")
	style.border_color = Color("a79669")
	style.set_border_width_all(1)
	style.set_corner_radius_all(8)
	style.content_margin_left = 16
	style.content_margin_right = 16
	style.content_margin_top = 14
	style.content_margin_bottom = 14
	panel.add_theme_stylebox_override("panel", style)
	for label: Label in [label_title, label_pos, label_chunk, label_terrain, label_id, label_quantity]:
		label.add_theme_font_size_override("font_size", 13)
		label.add_theme_color_override("font_color", Color("e5e8dc"))
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		label.custom_minimum_size = Vector2(280, 24)
	label_title.add_theme_font_size_override("font_size", 18)
	label_title.add_theme_color_override("font_color", Color("dfc68e"))
	var column := panel.get_node("VBoxContainer") as VBoxContainer
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.remove_child(column)
	panel.add_child(scroll)
	scroll.add_child(column)
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	get_viewport().size_changed.connect(_layout_panel)
	_layout_panel()


func _layout_panel() -> void:
	var viewport_size := get_viewport_rect().size
	panel.set_anchors_preset(Control.PRESET_TOP_LEFT)
	panel.position = Vector2(maxf(18, viewport_size.x - 354), 202)
	panel.size = Vector2(336, maxf(140, viewport_size.y - 312))


func refresh_entities(entities: Array, chunk_size: int) -> void:
	if _selected_entity_id.is_empty() or not panel.visible:
		return
	for value: Variant in entities:
		if value is Dictionary and str(value.get("id", "")) == _selected_entity_id:
			display_entity_info(value, chunk_size)
			return
	label_chunk.text = "No longer present in the live entity feed"
	label_id.text = "Last known position shown. The entity may be inactive or removed."
	label_quantity.text = "Live updates unavailable"

## Populates inspector fields for coordinates mapping.
func display_tile_info(tile_data: Dictionary, chunk_size: int) -> void:
	_selected_structure_id = ""
	_selected_entity_id = ""
	var x = tile_data["x"]
	var y = tile_data["y"]

	# Math-safe division flooring
	var cx: int = floori(float(x) / chunk_size)
	var cy: int = floori(float(y) / chunk_size)

	label_title.text = "Tile Inspector"
	label_pos.text = "World Position: (%d, %d)" % [x, y]
	label_chunk.text = "Chunk Position: (%d, %d)" % [cx, cy]
	label_terrain.text = "Terrain: %s" % str(tile_data["terrain"]).capitalize()
	var metadata: Dictionary = tile_data.get("metadata", {})
	label_id.text = "Elevation: %.2f   Fertility: %.2f\nMovement Cost: %.2f   Walkable: %s" % [
		float(metadata.get("elevation", 0.0)),
		float(metadata.get("fertility", 0.0)),
		float(tile_data.get("movement_cost", 1.0)),
		"YES" if bool(tile_data.get("walkable", true)) else "NO"
	]
	label_quantity.hide()

	panel.show()


func display_entity_info(entity: Dictionary, chunk_size: int) -> void:
	_selected_structure_id = ""
	var changed := _selected_entity_id != str(entity.get("id", "")) or not panel.visible
	_selected_entity_id = str(entity.get("id", ""))
	var x := int(entity.get("x", 0))
	var y := int(entity.get("y", 0))
	var needs: Dictionary = entity["needs"] if entity.get("needs") is Dictionary else {}
	var metadata: Dictionary = entity.get("metadata", {})
	var animal := str(entity.get("kind", "agent")).to_lower() == "animal"
	label_title.text = "%s · %s" % [str(metadata.get("species", "Animal")).capitalize() if animal else "Citizen", str(entity.get("name", "Unknown"))]
	label_pos.text = "Position: (%d, %d)   Chunk: (%d, %d)" % [x, y, floori(float(x) / chunk_size), floori(float(y) / chunk_size)]
	label_chunk.text = "NOW  %s" % str(entity.get("action", metadata.get("state", "idle"))).replace("_", " ").to_upper()
	if animal:
		label_chunk.text += " · %s · DAY %d" % [str(metadata.get("age_stage", "unknown")).to_upper(), int(metadata.get("age_days", 0))]
	elif metadata.has("life_stage"):
		label_chunk.text += " · %s · AGE %d" % [str(metadata["life_stage"]).to_upper(), int(metadata.get("age_days", 0)) / 365]
	var lines := PackedStringArray()
	for key: String in ["health", "energy", "hunger", "thirst"]:
		lines.append("%s: %s" % [key.capitalize(), "%.0f / 100" % float(needs[key]) if needs.has(key) else "Unavailable"])
	label_terrain.text = "\n".join(lines)
	label_terrain.custom_minimum_size.y = 76
	var target: Dictionary = entity.get("action_target", {})
	label_id.text = "Target: (%s, %s)" % [target["x"], target["y"]] if target.has("x") and target.has("y") else "Target: not reported"
	if animal:
		label_id.text += "\n" + str(metadata.get("lifestyle", "Lifestyle not yet observed."))
		if metadata.has("home_x") and metadata.has("home_y"):
			label_id.text += "\nHome territory: (%s, %s)" % [metadata["home_x"], metadata["home_y"]]
		if metadata.has("mother_id"):
			label_id.text += "\nFamily: offspring with a recorded parent"
		if metadata.has("seasonal_state"):
			label_id.text += "\nSeasonal activity: " + str(metadata["seasonal_state"]).capitalize()
	if not animal:
		label_id.text += "\nGoal: %s" % str(entity.get("goal", "idle")).replace("_", " ")
		label_id.text += "\nWork progress: %.0f%%" % (float(entity.get("action_progress", 0.0)) * 100)
	var route: Array = entity.get("route", [])
	if not route.is_empty():
		label_id.text += "\nRoute: %d steps · %s" % [route.size(), str(entity.get("route_status", "moving"))]
	if bool(entity.get("indoors", false)):
		label_id.text += "\nResting in assigned shelter"
	if not str(entity.get("decision_reason", "")).is_empty():
		label_id.text += "\nWhy: " + str(entity["decision_reason"])
	var inventory: Dictionary = entity["inventory"] if entity.get("inventory") is Dictionary else {}
	var items: Dictionary = inventory.get("items", {})
	var contents := PackedStringArray()
	for item: String in items:
		contents.append("%s %.1f" % [item.replace("_", " ").capitalize(), float(items[item])])
	label_quantity.text = "Inventory: " + (", ".join(contents) if not contents.is_empty() else "Empty" if not animal else "Not applicable")
	label_quantity.custom_minimum_size.y = 44
	label_quantity.show()
	panel.show()
	if changed:
		if _entry_tween != null:
			_entry_tween.kill()
		panel.modulate.a = 0.0
		_entry_tween = create_tween()
		_entry_tween.tween_property(panel, "modulate:a", 1.0, 0.18)


func display_entity_observation(observation: Dictionary) -> void:
	# Detailed historical responses must not overwrite a newer live selection.
	if not _selected_entity_id.is_empty():
		return
	var memories: Array = observation.get("memories", [])
	var relationships: Array = observation.get("relationships", [])
	var communications: Array = observation.get("communications", [])
	var history: Dictionary = observation.get("history", {})
	var knowledge: Dictionary = observation.get("knowledge", {})
	var availability: Dictionary = observation.get("availability", {})
	label_quantity.text = "MEMORY %d   ACTIONS %d   RELATIONSHIPS %d\nKNOWLEDGE %d tiles · %d resources   MESSAGES %d\nMOOD %s   AGE %s" % [
		memories.size(), history.get("actions", []).size(), relationships.size(),
		knowledge.get("tiles", {}).size(), knowledge.get("resources", {}).size(),
		communications.size(),
		str(availability.get("mood", "not_implemented")).replace("_", " ").to_upper(),
		str(availability.get("age", "not_implemented")).replace("_", " ").to_upper()
	]


## Displays a backend-owned resource located on the selected tile.
func display_resource_info(resource_data: Dictionary, chunk_size: int) -> void:
	_selected_structure_id = ""
	_selected_entity_id = ""
	var x: int = int(resource_data["x"])
	var y: int = int(resource_data["y"])
	var cx: int = floori(float(x) / chunk_size)
	var cy: int = floori(float(y) / chunk_size)

	label_title.text = "Resource Inspector"
	label_pos.text = "World Position: (%d, %d)" % [x, y]
	label_chunk.text = "Chunk Position: (%d, %d)" % [cx, cy]
	label_terrain.text = "Resource: %s" % str(resource_data["type"]).capitalize()
	label_id.text = "Resource ID: %s" % str(resource_data["id"])
	label_quantity.text = "Quantity: %.1f / %.1f" % [
		float(resource_data["quantity"]), float(resource_data["capacity"])
	]
	if str(resource_data.get("produce_type", "")) != "":
		label_quantity.text += "\n%s: %.1f / %.1f" % [
			str(resource_data["produce_type"]).capitalize(),
			float(resource_data.get("produce_quantity", 0.0)),
			float(resource_data.get("produce_capacity", 0.0))
		]
	label_quantity.show()

	panel.show()


func display_structure_info(structure: Dictionary) -> void:
	_selected_entity_id = ""
	_selected_structure_id = str(structure.get("id", ""))
	label_title.text = str(structure.get("structure_type", "Structure")).capitalize()
	label_pos.text = "Position: (%s, %s)" % [structure.get("x", 0), structure.get("y", 0)]
	label_chunk.text = "Operational" if structure.get("completed", false) else "Under construction"
	label_terrain.text = "Construction: %.0f%%" % (float(structure.get("progress_ratio", 0)) * 100)
	var stock: Dictionary = structure.get("stockpile", {})
	var items: Dictionary = stock.get("items", {})
	var lines := PackedStringArray()
	var used := 0.0
	for item: String in items:
		used += float(items[item])
		lines.append("%s: %.1f" % [item.capitalize(), float(items[item])])
	label_id.text = "Storage: %.1f / %.1f" % [used, float(stock.get("capacity", 0))] if str(structure.get("structure_type", "")) == "storage" else "Materials committed to construction"
	label_quantity.text = "\n".join(lines) if not lines.is_empty() else "No stored materials"
	var kind := str(structure.get("structure_type", "")).to_lower()
	if kind in ["campfire", "torch"]:
		label_quantity.text = "Fuel: %.1f wood · %s" % [float(structure.get("fuel", 0)), "Burning" if float(structure.get("fuel", 0)) > 0 else "Unlit"]
	elif kind == "farm":
		label_quantity.text = "Crop growth: %.0f%%\nHarvestable food: %.1f" % [float(structure.get("crop_growth", 0)) * 100, float(structure.get("crop_food", 0))]
	label_quantity.show()
	panel.modulate.a = 1.0
	panel.show()


func refresh_structures(structures: Array) -> void:
	if not panel.visible or _selected_structure_id.is_empty():
		return
	for structure: Dictionary in structures:
		if str(structure.get("id", "")) == _selected_structure_id:
			display_structure_info(structure)
			return
	label_chunk.text = "Structure no longer available"


func _on_close_button_pressed() -> void:
	_selected_structure_id = ""
	_selected_entity_id = ""
	panel.hide()


func hide_inspector() -> void:
	_selected_structure_id = ""
	_selected_entity_id = ""
	panel.hide()
