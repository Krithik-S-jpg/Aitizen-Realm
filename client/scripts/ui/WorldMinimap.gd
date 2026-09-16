extends Control
class_name WorldMinimap

## Compact observer map derived exclusively from loaded backend world state.

signal navigate_requested(map_position: Vector2i)

const DEFAULT_TERRAIN_COLORS := {
	"water": Color("3188c8"), "ocean": Color("185b98"), "grass": Color("3f9b55"),
	"forest": Color("216f42"), "sand": Color("d5b86b"), "desert": Color("bd7d3e"),
	"stone": Color("747b80"), "mountain": Color("535b61"), "snow": Color("dce9e8"),
	"ice": Color("81c5d4"), "wetland": Color("39745d"), "tundra": Color("aabdb7")
}

var _world: Dictionary = {}
var _camera_position := Vector2i.ZERO
var _terrain_colors: Dictionary = DEFAULT_TERRAIN_COLORS.duplicate()
var _background := Color("071722f2")
var _border := Color("376672")


func _ready() -> void:
	_load_theme_config()
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	gui_input.connect(_on_gui_input)


func update_world(world: Dictionary) -> void:
	_world = world
	queue_redraw()


func update_camera(map_position: Vector2i) -> void:
	_camera_position = map_position
	queue_redraw()


func _draw() -> void:
	draw_style_box(_map_style(), Rect2(Vector2.ZERO, size))
	if _world.is_empty():
		draw_string(ThemeDB.fallback_font, Vector2(12, 28), "MINIMAP · WAITING", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color("8ca2aa"))
		return
	var width := maxi(int(_world.get("width", 1)), 1)
	var height := maxi(int(_world.get("height", 1)), 1)
	var map_rect := Rect2(10, 24, size.x - 20, size.y - 34)
	draw_rect(map_rect, Color("02080b"), true)
	for coordinate: Vector2i in _world.get("tiles", {}):
		var tile: Dictionary = _world["tiles"][coordinate]
		var point := Vector2(
			map_rect.position.x + float(coordinate.x) / width * map_rect.size.x,
			map_rect.position.y + float(coordinate.y) / height * map_rect.size.y
		)
		var cell := Vector2(maxf(1.0, map_rect.size.x / width + 0.5), maxf(1.0, map_rect.size.y / height + 0.5))
		draw_rect(Rect2(point, cell), _terrain_colors.get(str(tile.get("terrain", "grass")), Color("55736a")), true)
	for structure: Dictionary in _world.get("structures", []):
		_draw_marker(map_rect, width, height, int(structure["x"]), int(structure["y"]), Color("efc05f"), 2.5)
	for entity: Dictionary in _world.get("entities", []):
		_draw_marker(map_rect, width, height, int(entity["x"]), int(entity["y"]), Color("6cf1e0"), 2.0)
	var camera_point := Vector2(
		map_rect.position.x + float(_camera_position.x) / width * map_rect.size.x,
		map_rect.position.y + float(_camera_position.y) / height * map_rect.size.y
	)
	var view_size := Vector2(
		clampf(map_rect.size.x * 16.0 / width, 12.0, map_rect.size.x),
		clampf(map_rect.size.y * 16.0 / height, 9.0, map_rect.size.y)
	)
	draw_rect(Rect2(camera_point - view_size * 0.5, view_size), Color("fff0ac"), false, 2.0)
	draw_string(ThemeDB.fallback_font, Vector2(10, 16), "WORLD MAP", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color("72d6bb"))
	draw_string(ThemeDB.fallback_font, Vector2(size.x - 72, 16), "%d × %d" % [width, height], HORIZONTAL_ALIGNMENT_RIGHT, 62, 9, Color("91a8af"))


func _draw_marker(rect: Rect2, width: int, height: int, x: int, y: int, color: Color, radius: float) -> void:
	var point := rect.position + Vector2(float(x) / width * rect.size.x, float(y) / height * rect.size.y)
	draw_circle(point, radius, color)


func _on_gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed and not _world.is_empty():
		var map_rect := Rect2(10, 24, size.x - 20, size.y - 34)
		if not map_rect.has_point(event.position):
			return
		var normalized: Vector2 = (event.position - map_rect.position) / map_rect.size
		navigate_requested.emit(Vector2i(
			clampi(roundi(normalized.x * int(_world["width"])), 0, int(_world["width"]) - 1),
			clampi(roundi(normalized.y * int(_world["height"])), 0, int(_world["height"]) - 1)
		))


func _load_theme_config() -> void:
	var file := FileAccess.open("res://config/minimap_theme.json", FileAccess.READ)
	if file == null:
		return
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		return
	var config: Dictionary = parsed
	_background = Color(str(config.get("background", _background.to_html())))
	_border = Color(str(config.get("border", _border.to_html())))
	var colors: Dictionary = config.get("terrain_colors", {})
	for terrain: Variant in colors:
		_terrain_colors[str(terrain)] = Color(str(colors[terrain]))


func _map_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = _background
	style.border_color = _border
	style.set_border_width_all(1)
	style.set_corner_radius_all(9)
	return style
