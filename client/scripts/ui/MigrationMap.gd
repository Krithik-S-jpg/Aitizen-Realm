extends Control

var points: Array = []

func _ready() -> void:
	custom_minimum_size = Vector2(300, 135)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)

func set_points(values: Array) -> void:
	points = values
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color("102624"))
	draw_string(ThemeDB.fallback_font, Vector2(12, 21), "OBSERVED TRAIL · dashed gaps are not verified paths", HORIZONTAL_ALIGNMENT_LEFT, size.x - 24, 12, Color("d7c79c"))
	if points.is_empty():
		return
	var minimum := Vector2(float(points[0][0]), float(points[0][1]))
	var maximum := minimum
	for point: Array in points:
		minimum = minimum.min(Vector2(point[0], point[1]))
		maximum = maximum.max(Vector2(point[0], point[1]))
	var extent := (maximum - minimum).max(Vector2.ONE)
	var previous := Vector2.ZERO
	for index in range(points.size()):
		var raw := Vector2(points[index][0], points[index][1])
		var at := Vector2(30, 47) + (raw - minimum) / extent * Vector2(maxf(30, size.x - 85), maxf(20, size.y - 75))
		if index > 0:
			draw_dashed_line(previous, at, Color("568f85"), 2, 5)
		draw_circle(at, 5, Color("e8c879") if index == points.size() - 1 else Color("75c5b4"))
		draw_string(ThemeDB.fallback_font, at + Vector2(7, -7), "%d · (%d,%d)" % [index + 1, raw.x, raw.y], HORIZONTAL_ALIGNMENT_LEFT, 100, 10, Color("c7d9d2"))
		previous = at
