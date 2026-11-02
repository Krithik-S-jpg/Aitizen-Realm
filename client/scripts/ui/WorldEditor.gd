extends PanelContainer

signal terrain_changed
var renderer: WorldRenderer
var _request: HTTPRequest
var _terrain: OptionButton
var _tool: OptionButton
var _radius: OptionButton
var _status: Label
var _apply: Button
var _brush := {}
var _operation := ""
var _busy := false
var _outline: Node2D

func _ready() -> void:
	position = Vector2(244, 160)
	custom_minimum_size = Vector2(370, 210)
	var margin := MarginContainer.new()
	for side: String in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 12)
	add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 7)
	margin.add_child(column)
	var title := Label.new()
	title.text = "WORLD EDITOR · PAUSED TOOLS"
	column.add_child(title)
	var designer := preload("res://scripts/ui/ScenarioDesigner.gd").new()
	add_child(designer)
	var design_button := Button.new()
	design_button.text = "Open scenario designer…"
	design_button.pressed.connect(func(): designer.popup_centered_clamped(Vector2i(980, 680)); designer._send("get"))
	column.add_child(design_button)
	_tool = OptionButton.new()
	for mode: String in ["Terrain", "Resource", "Weather", "Scenario"]:
		_tool.add_item(mode)
	column.add_child(_tool)
	_terrain = OptionButton.new()
	for kind: String in ["Grass", "Dirt", "Sand", "Forest", "Water", "Stone", "Mountain"]:
		_terrain.add_item(kind)
	column.add_child(_terrain)
	_tool.item_selected.connect(_change_tool)
	_radius = OptionButton.new()
	for label: String in ["Single tile", "Small brush · 5 tiles", "Wide brush · 13 tiles"]:
		_radius.add_item(label)
	column.add_child(_radius)
	for option: OptionButton in [_terrain, _radius]:
		option.item_selected.connect(func(_index: int) -> void: _invalidate())
	_status = Label.new()
	_status.text = "Pause, then click the world to preview.\nForest paints terrain only; it does not plant trees."
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.custom_minimum_size = Vector2(350, 60)
	column.add_child(_status)
	var row := HBoxContainer.new()
	column.add_child(row)
	_apply = Button.new()
	_apply.text = "Apply preview"
	_apply.disabled = true
	_apply.pressed.connect(func() -> void: _send("apply"))
	row.add_child(_apply)
	var undo := Button.new()
	undo.text = "Undo"
	undo.pressed.connect(func() -> void: _send("undo"))
	row.add_child(undo)
	var close := Button.new()
	close.text = "Close"
	close.pressed.connect(hide)
	row.add_child(close)
	_request = HTTPRequest.new()
	_request.timeout = 15
	add_child(_request)
	_request.request_completed.connect(_completed)
	_outline = Node2D.new()
	_outline.z_index = 80
	renderer.add_child(_outline)
	_outline.draw.connect(_draw_preview)
	visibility_changed.connect(func() -> void:
		_invalidate()
		_outline.visible = visible)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(self)
	hide()

func _invalidate() -> void:
	_brush.clear()
	_apply.disabled = true
	if is_instance_valid(_outline):
		_outline.queue_redraw()

func select_tile(coordinate: Vector2i) -> void:
	if _busy:
		return
	if renderer.underwater_view or renderer.cave_view:
		_status.text = "Switch to Surface before editing."
		return
	_brush = {"x": coordinate.x, "y": coordinate.y, "radius": _radius.selected, "tool": _tool.get_item_text(_tool.selected).to_lower(), "terrain": _terrain.get_item_text(_terrain.selected)}
	_send("preview")

func _send(operation: String) -> void:
	if _busy:
		return
	_operation = operation
	_busy = true
	for option: OptionButton in [_tool, _terrain, _radius]:
		option.disabled = true
	_apply.disabled = true
	var payload := {"x": _brush.get("x", 0), "y": _brush.get("y", 0), "radius": _brush.get("radius", 0), "terrain": _brush.get("terrain", "Grass"), "token": _brush.get("token", "")}
	payload["tool"] = _brush.get("tool", "terrain")
	var error := _request.request(RuntimeConfig.http_url("/api/v1/world/editor/" + operation), PackedStringArray(["Content-Type: application/json"]), HTTPClient.METHOD_POST, JSON.stringify(payload))
	if error != OK:
		_busy = false
		for option: OptionButton in [_tool, _terrain, _radius]:
			option.disabled = false
		_status.text = "Could not send editor request."
	else:
		_status.text = "Checking editor request…"

func _completed(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_busy = false
	for option: OptionButton in [_tool, _terrain, _radius]:
		option.disabled = false
	var decoder := JSON.new()
	var data: Variant = decoder.data if decoder.parse(body.get_string_from_utf8()) == OK else null
	if result != HTTPRequest.RESULT_SUCCESS or code >= 400 or not data is Dictionary:
		_status.text = str(data.get("detail", "Request could not be confirmed; reload before retrying.")) if data is Dictionary else "Connection failed; reload before retrying."
		_invalidate()
		return
	if _operation == "preview" and visible and not _brush.is_empty():
		_brush.merge(data, true)
		_apply.disabled = not bool(data.get("can_apply", false))
		_status.text = "%d tiles · %s" % [data.get("tiles", []).size(), "Ready to apply" if data.get("can_apply", false) else "Blocked: " + "; ".join(data.get("blocked", []))]
		if data.get("can_apply", false):
			_status.text += "\n" + str(data.get("description", "Terrain change only; objects are not created."))
		_outline.queue_redraw()
	elif _operation != "preview":
		_status.text = "%d tiles updated. Reloading world…" % data.get("changed", 0)
		_invalidate()
		terrain_changed.emit()

func _draw_preview() -> void:
	for tile: Dictionary in _brush.get("tiles", []):
		var center := renderer.map_to_local(Vector2i(int(tile.x), int(tile.y)))
		var color := Color(.35, .95, .7, .5) if _brush.get("can_apply", false) else Color(1, .25, .2, .55)
		_outline.draw_colored_polygon(renderer._diamond_at(center), color)

func _change_tool(index: int) -> void:
	_invalidate()
	_terrain.clear()
	var choices: Array = [["Grass", "Dirt", "Sand", "Forest", "Water", "Stone", "Mountain"], ["Tree", "Stone", "Bush", "Herb", "Ore"], ["Rain", "Snow", "Clear"], ["FOOD_GROVE", "STONE_OUTCROP", "RAIN_TEST", "DRY_SPELL"]][index]
	for choice: String in choices:
		_terrain.add_item(choice)
	_status.text = "Click the surface to preview. Weather lasts 48 ticks; resource presets place finite supplies."
