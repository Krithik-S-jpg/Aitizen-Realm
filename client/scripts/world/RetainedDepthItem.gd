extends Node2D

# Each CanvasItem retains its draw commands until the content changes.
# All positions remain in the renderer's coordinate system for exact depth order.
var renderer: Node2D
var item: Dictionary = {}
var highlight := false
var last_paint := -1.0
var phase := 0.0

func _draw() -> void:
	if not is_instance_valid(renderer):
		return
	renderer._paint_target = self
	if highlight:
		renderer._draw_highlight(renderer._hovered_tile,renderer.HOVER_COLOR,1.5)
		renderer._draw_highlight(renderer._selected_tile,renderer.SELECTED_COLOR,2.5)
	else:
		renderer._paint_depth_item(item)
	renderer._paint_target = null
	last_paint = renderer._visual_seconds
