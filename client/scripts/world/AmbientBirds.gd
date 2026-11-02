extends Node2D

## Bounded decorative flocks: no gameplay entities or per-frame node allocation.
var renderer: WorldRenderer
var running := true
var quality := 1.0
var activity := 1.0
var target_activity := 1.0
var elapsed := 0.0
var wind := Vector2.ZERO
var anchors: Array[Vector2] = []

func configure(calendar: Dictionary) -> void:
	var night := str(calendar.get("phase", "DAY")).to_upper() == "NIGHT"
	var storm := str(calendar.get("weather", "CLEAR")).to_upper() == "RAIN" and float(calendar.get("weather_intensity", 0)) >= .65
	target_activity = 0.0 if night or storm else 1.0
	wind = Vector2.from_angle(deg_to_rad(float(calendar.get("wind_direction", 0)))) * minf(12, float(calendar.get("wind_speed", 0)))

func rebuild_habitats(tiles: Dictionary) -> void:
	anchors.clear()
	# Stable map coordinates keep flocks in world space while the camera moves.
	for coordinate: Vector2i in tiles:
		if str(tiles[coordinate].get("terrain", "")).to_lower() in ["forest", "grass", "meadow"] and posmod(coordinate.x * 17 + coordinate.y * 31, 47) == 0:
			anchors.append(renderer.map_to_local(coordinate))
			if anchors.size() >= 8:
				break

func _process(delta: float) -> void:
	visible = is_instance_valid(renderer) and not renderer.underwater_view and not renderer.cave_view
	if not visible or not running:
		return
	if not preload("res://scripts/ui/AtlasTheme.gd").reduced_motion:
		elapsed += delta
	activity = move_toward(activity, target_activity, delta * .4)
	queue_redraw()

func _draw() -> void:
	if activity <= .001 or anchors.is_empty():
		return
	var inverse := get_global_transform_with_canvas().affine_inverse()
	var view := Rect2(inverse * Vector2.ZERO, Vector2.ZERO).expand(inverse * get_viewport_rect().size).grow(100)
	var count := roundi(12 * quality)
	for index in range(count):
		var flock := index / 4
		var phase := elapsed * .22 + flock * 1.8
		var heading := Vector2(-sin(phase) * 95, cos(phase) * 42).normalized()
		var ground := anchors[flock % anchors.size()] + Vector2(cos(phase) * 95, sin(phase) * 42) + Vector2(index % 4 * -17, index % 3 * 12) + wind
		if not view.has_point(ground) or not renderer._tiles.has(renderer.local_to_map(ground)):
			continue
		draw_set_transform(ground, 0, Vector2(1.6, .55))
		draw_circle(Vector2.ZERO, 3.5, Color(0.02, .08, .12, .15 * activity))
		var bird := ground - Vector2(0, 48 + sin(elapsed + index) * 4)
		var flap := sin(elapsed * 10 + index * .8) if fmod(elapsed + index, 5) < 3 else .15
		draw_set_transform(bird, heading.angle(), Vector2.ONE)
		var wings := PackedVector2Array([Vector2(5, 0), Vector2(0, -2), Vector2(-2, -7 - flap * 3), Vector2(-5, -3), Vector2(-3, 0), Vector2(-5, 3), Vector2(-2, 7 + flap * 3), Vector2(0, 2)])
		draw_colored_polygon(wings, Color(.12, .22, .29, activity))
		draw_line(Vector2(-3, 0), Vector2(4, 0), Color(.79, .83, .75, activity), 1.4, true)
		draw_line(Vector2(-3, 0), Vector2(-8, -2), Color(.1, .17, .22, activity), 1.5, true)
		draw_line(Vector2(-3, 0), Vector2(-8, 2), Color(.1, .17, .22, activity), 1.5, true)
		draw_set_transform(Vector2.ZERO)
