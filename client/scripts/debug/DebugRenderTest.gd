# DebugRenderTest.gd
extends Node2D

## An isolated debug renderer to verify direct screen-space isometric drawing capabilities.

@export var tile_width: float = 64.0
@export var tile_height: float = 32.0

var _draw_printed: bool = false

func _ready() -> void:
	print("=== DEBUG RENDERER ACTIVE ===")

	# Output runtime diagnostic values
	print("Active Scene: res://scenes/Main.tscn")
	print("Debug Node Path: %s" % str(get_path()))
	print("Debug Node Visible: %s" % str(visible))
	print("Viewport Size: %s" % str(get_viewport_rect().size))

func _draw() -> void:
	if not _draw_printed:
		print("=== DEBUG DRAW EXECUTED ===")
		_draw_printed = true

	# Find viewport center
	var viewport_size = get_viewport_rect().size
	var center_x = viewport_size.x / 2.0
	var center_y = viewport_size.y / 2.0

	# Draw a 5x5 grid of isometric colored diamonds
	for x in range(5):
		for y in range(5):
			# Map coordinates to isometric screen space
			var screen_x = center_x + (x - y) * tile_width / 2.0
			var screen_y = center_y + (x + y) * tile_height / 2.0
			var center = Vector2(screen_x, screen_y)

			# Define diamond points
			var top = center + Vector2(0, -tile_height / 2.0)
			var right = center + Vector2(tile_width / 2.0, 0)
			var bottom = center + Vector2(0, tile_height / 2.0)
			var left = center + Vector2(-tile_width / 2.0, 0)

			var points = PackedVector2Array([top, right, bottom, left])

			# Cycle colors for high visibility (different flat colors)
			var color = Color.GREEN
			if (x + y) % 3 == 0:
				color = Color.GOLD
			elif (x + y) % 3 == 1:
				color = Color.ORANGE_RED

			# Draw flat filled diamond
			draw_polygon(points, PackedColorArray([color]))

			# Draw visible border
			var outline_points = PackedVector2Array([top, right, bottom, left, top])
			draw_polyline(outline_points, Color.WHITE, 1.5)
