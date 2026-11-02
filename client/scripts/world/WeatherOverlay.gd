# WeatherOverlay.gd
extends Node2D
class_name WeatherOverlay

## Draws precipitation inside one backend-defined region of the world.

var _weather: String = "CLEAR"
var _intensity: float = 0.0
var _wind_speed: float = 4.0
var _wind_direction: float = 0.0
var _elapsed: float = 0.0
var _display_intensity: float = 0.0
var _region_center: Vector2 = Vector2.ZERO
var _region_radius_x: float = 320.0
var _region_radius_y: float = 160.0
var _simulation_running := true
var _local_view_rect := Rect2()
var _quality_scale := 1.0
var renderer: WorldRenderer
var _patches: Array = []
var _drawing_patch := -1


func set_patches(patches: Array) -> void:
	_patches = patches.slice(0, 4).duplicate(true)
	queue_redraw()


func _allows_point(point: Vector2) -> bool:
	if not is_instance_valid(renderer):
		return true
	var tile := renderer.local_to_map(point)
	if not renderer._tiles.has(tile):
		return false
	for index in range(_patches.size() - 1, -1, -1):
		var patch: Dictionary = _patches[index]
		if Vector2(tile).distance_squared_to(Vector2(patch.x, patch.y)) <= float(patch.radius) * float(patch.radius):
			return index == _drawing_patch
	return _drawing_patch == -1


func configure(
	weather: String,
	intensity: float,
	wind_speed: float,
	wind_direction: float,
	region_center: Vector2,
	radius_tiles: int,
	tile_width: float,
	tile_height: float
) -> void:
	_weather = weather.to_upper()
	_intensity = clampf(intensity, 0.0, 1.0)
	_wind_speed = maxf(wind_speed, 0.0)
	_wind_direction = wind_direction
	_region_center = region_center
	_region_radius_x = maxf(float(radius_tiles) * tile_width, tile_width)
	_region_radius_y = maxf(float(radius_tiles) * tile_height, tile_height)
	queue_redraw()


func _process(delta: float) -> void:
	visible = not is_instance_valid(renderer) or (not renderer.underwater_view and not renderer.cave_view)
	if not visible:
		return
	if not _simulation_running:
		return
	if not preload("res://scripts/ui/AtlasTheme.gd").reduced_motion:
		_elapsed += delta
	var was_visible := _display_intensity > 0.0
	_display_intensity = move_toward(
		_display_intensity,
		_intensity if _weather != "CLEAR" else 0.0,
		delta * 0.3
	)
	if was_visible or _display_intensity > 0.001 or not _patches.is_empty():
		queue_redraw()


func set_simulation_running(running: bool) -> void:
	_simulation_running = running


func set_visual_quality(quality: String) -> void:
	_quality_scale = {"performance": 0.45, "balanced": 0.72, "high": 1.0}.get(quality.to_lower(), 1.0)
	queue_redraw()


func _draw() -> void:
	_update_local_view_rect()
	_drawing_patch = -1
	_draw_region()
	if not is_instance_valid(renderer):
		return
	var saved_center := _region_center
	var saved_x := _region_radius_x
	var saved_y := _region_radius_y
	var saved_weather := _weather
	var saved_intensity := _display_intensity
	for index in range(_patches.size()):
		var patch: Dictionary = _patches[index]
		_drawing_patch = index
		_weather = str(patch.weather)
		_display_intensity = float(patch.intensity)
		_region_center = renderer.map_to_local(Vector2i(patch.x, patch.y))
		_region_radius_x = (float(patch.radius) + 1.0) * renderer.tile_width
		_region_radius_y = (float(patch.radius) + 1.0) * renderer.tile_height
		_draw_region()
	_region_center = saved_center
	_region_radius_x = saved_x
	_region_radius_y = saved_y
	_weather = saved_weather
	_display_intensity = saved_intensity
	_drawing_patch = -1


func _draw_region() -> void:
	if _display_intensity <= 0.001:
		return
	_update_local_view_rect()
	var weather_bounds := Rect2(
		_region_center - Vector2(_region_radius_x, _region_radius_y),
		Vector2(_region_radius_x * 2.0, _region_radius_y * 2.0)
	)
	if not _local_view_rect.intersects(weather_bounds):
		return
	if _weather == "RAIN":
		_draw_rain(roundi((220.0 if _drawing_patch == -1 else 60.0) * _quality_scale))
		_draw_splashes(roundi((65.0 if _drawing_patch == -1 else 18.0) * _quality_scale))
	elif _weather == "SNOW":
		_draw_snow(roundi((130.0 if _drawing_patch == -1 else 40.0) * _quality_scale))


func _draw_rain(max_count: int) -> void:
	var count: int = roundi(float(max_count) * _display_intensity)
	var wind_x: float = sin(deg_to_rad(_wind_direction)) * (3.0 + _wind_speed * 0.45)
	for index in range(count):
		var normalized_x: float = fposmod(float(index * 97) / 500.0 + _elapsed * wind_x * .025, 2.0) - 1.0
		var speed: float = 150.0 + float(index % 7) * 24.0
		var normalized_y: float = fmod(float(index * 53) + _elapsed * speed, _region_radius_y * 2.0) / _region_radius_y - 1.0
		if normalized_x * normalized_x + normalized_y * normalized_y > 1.0:
			continue
		var start := _region_center + Vector2(
			normalized_x * _region_radius_x,
			normalized_y * _region_radius_y
		)
		if not _local_view_rect.has_point(start) or not _allows_point(start):
			continue
		if is_instance_valid(renderer) and not renderer._tiles.has(renderer.local_to_map(start)):
			continue
		var depth: float = 0.65 + float(index % 4) * 0.12
		draw_line(
			start,
			start + Vector2(wind_x * depth, 11.0 + 8.0 * depth),
			Color(0.63, 0.82, 1.0, 0.40 + depth * 0.28),
			1.0 + depth * 0.55,
			true
		)


func _draw_splashes(max_count: int) -> void:
	var count: int = roundi(float(max_count) * _display_intensity)
	for index in range(count):
		var cycle: float = fmod(_elapsed * 2.7 + float(index) * 0.41, 1.0)
		if cycle > 0.65:
			continue
		var angle: float = float(index * 137) * 0.11
		var distance: float = sqrt(float((index * 71) % 100) / 100.0)
		var splash_position := _region_center + Vector2(
			cos(angle) * distance * _region_radius_x,
			sin(angle) * distance * _region_radius_y
		)
		if not _local_view_rect.has_point(splash_position) or not _allows_point(splash_position):
			continue
		var water := false
		if is_instance_valid(renderer):
			var coordinate := renderer.local_to_map(splash_position)
			if not renderer._tiles.has(coordinate):
				continue
			var tile: Dictionary = renderer._tiles[coordinate]
			water = str(tile.get("terrain", "")).to_lower() in ["water", "ocean"] or bool(tile.get("metadata", {}).get("flooded", false))
		var alpha := (1.0 - cycle / .65) * .55
		if water:
			draw_set_transform(splash_position, 0, Vector2(1, .48))
			draw_arc(Vector2.ZERO, 2 + cycle * 14, 0, TAU, 18, Color(.7, .87, .96, alpha), 1, true)
			draw_set_transform(Vector2.ZERO)
		elif cycle < .3:
			var spread := cycle * 12
			draw_line(splash_position, splash_position + Vector2(-spread, -3 + cycle * 8), Color(.72, .88, 1, alpha), 1, true)
			draw_line(splash_position, splash_position + Vector2(spread, -3 + cycle * 8), Color(.72, .88, 1, alpha), 1, true)


func _draw_snow(max_count: int) -> void:
	var count: int = roundi(float(max_count) * _display_intensity)
	for index in range(count):
		var normalized_x: float = float((index * 109) % 1000) / 500.0 - 1.0
		var speed: float = 25.0 + float(index % 6) * 8.0
		var normalized_y: float = fmod(float(index * 61) + _elapsed * speed, _region_radius_y * 2.0) / _region_radius_y - 1.0
		if normalized_x * normalized_x + normalized_y * normalized_y > 1.0:
			continue
		var drift: float = sin(_elapsed + float(index)) * (5.0 + _wind_speed)
		var flake_position := _region_center + Vector2(
			normalized_x * _region_radius_x + drift,
			normalized_y * _region_radius_y
		)
		if not _local_view_rect.has_point(flake_position) or not _allows_point(flake_position):
			continue
		draw_circle(flake_position, 1.8 + float(index % 3) * 0.7, Color(1.0, 1.0, 1.0, 0.82))


func _update_local_view_rect() -> void:
	var inverse := get_global_transform_with_canvas().affine_inverse()
	var viewport_size := get_viewport_rect().size
	var points := PackedVector2Array([
		inverse * Vector2.ZERO,
		inverse * Vector2(viewport_size.x, 0.0),
		inverse * Vector2(0.0, viewport_size.y),
		inverse * viewport_size
	])
	var minimum := points[0]
	var maximum := points[0]
	for point: Vector2 in points:
		minimum = Vector2(minf(minimum.x, point.x), minf(minimum.y, point.y))
		maximum = Vector2(maxf(maximum.x, point.x), maxf(maximum.y, point.y))
	_local_view_rect = Rect2(minimum, maximum - minimum).grow(24.0)
