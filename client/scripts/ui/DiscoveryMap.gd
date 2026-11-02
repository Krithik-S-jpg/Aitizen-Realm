extends Control

var entries: Array = []
var selected := ""

func _ready() -> void:
	custom_minimum_size = Vector2(300, 120)

func set_entries(values: Array, selection: String) -> void:
	entries = values
	selected = selection
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color("102624"))
	draw_string(ThemeDB.fallback_font, Vector2(15, 23), "FIELD SKETCH / EVIDENCE TRAIL", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("d7c79c"))
	var kind := "inscription"
	for entry: Dictionary in entries:
		if str(entry.get("id", "")) == selected:
			kind = str(entry.get("kind", "inscription"))
	draw_set_transform(Vector2(65, 92))
	preload("res://scripts/world/AntiquityVisuals.gd").paint(self, kind)
	draw_set_transform(Vector2.ZERO)
	if entries.is_empty():
		draw_string(ThemeDB.fallback_font, Vector2(140, 80), "No discoveries yet. Let curious citizens explore.", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("99b6af"))
		return
	var maximum := Vector2.ONE
	for entry: Dictionary in entries:
		maximum = maximum.max(Vector2(float(entry.x) + 1, float(entry.y) + 1))
	var points := {}
	for entry: Dictionary in entries:
		points[str(entry.id)] = Vector2(160, 48) + Vector2(float(entry.x), float(entry.y)) / maximum * Vector2(maxf(80, size.x - 205), maxf(20, size.y - 72))
	for entry: Dictionary in entries:
		var point: Vector2 = points[str(entry.id)]
		var next_key := str(entry.get("next_id", ""))
		if points.has(next_key):
			draw_dashed_line(point, points[next_key], Color("588e82"), 1.5, 5)
	for index in range(entries.size()):
		var entry: Dictionary = entries[index]
		var point: Vector2 = points[str(entry.id)]
		draw_circle(point, 9, Color("e5c37d") if str(entry.id) == selected else Color("68baa5"))
		draw_string(ThemeDB.fallback_font, point + Vector2(-3, 4), str(index + 1), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("102624"))
		draw_string(ThemeDB.fallback_font, point + Vector2(12, 4), str(entry.get("kind", "ruin")).replace("_", " "), HORIZONTAL_ALIGNMENT_LEFT, 130, 11, Color("c1d3ca"))
