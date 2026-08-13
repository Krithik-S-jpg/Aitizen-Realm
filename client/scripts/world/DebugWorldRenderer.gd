# DebugWorldRenderer.gd
extends Node2D
class_name DebugWorldRenderer

## A temporary debug and fallback renderer using Node2D polygon drawing.
## Visualizes the world isometrically without any TileMap or TileSet dependency.

@export var tile_width: float = 64.0
@export var tile_height: float = 32.0

const COLORS: Dictionary = {
	"grass": Color(0.13, 0.55, 0.13),      # Forest Green
	"water": Color(0.12, 0.56, 1.0),       # Dodger Blue
	"dirt": Color(0.54, 0.27, 0.07),       # Saddle Brown
	"stone": Color(0.5, 0.5, 0.5),         # Grey
	"forest": Color(0.0, 0.39, 0.0),       # Dark Green
	"sand": Color(0.93, 0.91, 0.67)        # Pale Goldenrod
}
const DEFAULT_COLOR: Color = Color(0.8, 0.8, 0.8) # Light Grey Fallback
const OUTLINE_COLOR: Color = Color(0.0, 0.0, 0.0, 0.2) # Subtle transparent black

var _tiles_data: Dictionary = {}

func render_world(tiles: Dictionary) -> void:
	_tiles_data = tiles
	queue_redraw()

	# Diagnostics logging as per specs
	print("=== DebugWorldRenderer: Render Report ===")
	print("Rendered tiles: %d" % _tiles_data.size())
	print("=========================================")

func _draw() -> void:
	if _tiles_data.is_empty():
		return

	for coord in _tiles_data:
		var tile_data = _tiles_data[coord]
		var terrain = tile_data.get("terrain", "").to_lower()
		var color = COLORS.get(terrain, DEFAULT_COLOR)

		# Compute center of the tile
		var center = map_to_local(coord)

		# Define diamond points
		var top = center + Vector2(0, -tile_height / 2.0)
		var right = center + Vector2(tile_width / 2.0, 0)
		var bottom = center + Vector2(0, tile_height / 2.0)
		var left = center + Vector2(-tile_width / 2.0, 0)

		var points = PackedVector2Array([top, right, bottom, left])

		# Draw filled diamond
		draw_polygon(points, PackedColorArray([color]))

		# Draw subtle outline
		var outline_points = PackedVector2Array([top, right, bottom, left, top])
		draw_polyline(outline_points, OUTLINE_COLOR, 1.0)

## Computes the center pixel position of a map coordinate.
func map_to_local(map_pos: Vector2i) -> Vector2:
	return Vector2(
		(map_pos.x - map_pos.y) * tile_width / 2.0,
		(map_pos.x + map_pos.y) * tile_height / 2.0
	)

## Converts a pixel coordinate to map coordinate isometrically.
func world_to_map(pixel_pos: Vector2) -> Vector2i:
	var mx: float = (pixel_pos.x / tile_width) + (pixel_pos.y / tile_height)
	var my: float = (pixel_pos.y / tile_height) - (pixel_pos.x / tile_width)
	return Vector2i(floori(mx), floori(my))

## Compatibility helper with TileMapLayer API.
func local_to_map(local_pos: Vector2) -> Vector2i:
	return world_to_map(local_pos)

## Computes the used rectangle bounding box of the active tiles.
func get_used_rect() -> Rect2i:
	if _tiles_data.is_empty():
		return Rect2i(0, 0, 0, 0)

	var keys = _tiles_data.keys()
	var min_x: int = keys[0].x
	var max_x: int = keys[0].x
	var min_y: int = keys[0].y
	var max_y: int = keys[0].y

	for coord in keys:
		min_x = min(min_x, coord.x)
		max_x = max(max_x, coord.x)
		min_y = min(min_y, coord.y)
		max_y = max(max_y, coord.y)

	return Rect2i(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
