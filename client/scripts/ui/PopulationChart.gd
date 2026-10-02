extends Control

## Bounded chart of measured citizen population, with no synthetic samples.
var _samples: Array = []


func _ready() -> void:
	custom_minimum_size.y = 80
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)


func set_samples(samples: Array) -> void:
	_samples = samples.slice(maxi(0, samples.size() - 120))
	queue_redraw()


func _draw() -> void:
	var font := ThemeDB.fallback_font
	draw_string(font, Vector2(0, 14), "LIVING POPULATION · citizens and wildlife", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("93b5ac"))
	if _samples.is_empty():
		draw_string(font, Vector2(0, 40), "Start or step the world to collect observations.", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("93b5ac"))
		return
	var maximum := 1.0
	for sample: Dictionary in _samples:
		maximum = maxf(maximum, float(sample.get("population", 0)))
	var first_tick := float(_samples[0].get("tick", 0))
	var last_tick := float(_samples[-1].get("tick", first_tick))
	var points := PackedVector2Array()
	for sample: Dictionary in _samples:
		var x := (float(sample.get("tick", 0)) - first_tick) / maxf(1, last_tick - first_tick) * maxf(1, size.x - 45)
		points.append(Vector2(x, 65 - float(sample.get("population", 0)) / maximum * 38))
	if points.size() > 1:
		draw_polyline(points, Color("74d6b0"), 2, true)
	draw_circle(points[-1], 3, Color("c7efd9"))
	draw_string(font, Vector2(0, 79), "Tick %d → %d" % [int(first_tick), int(last_tick)], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color("93b5ac"))
	draw_string(font, Vector2(size.x - 40, 40), str(_samples[-1].get("population", 0)), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("c7efd9"))
