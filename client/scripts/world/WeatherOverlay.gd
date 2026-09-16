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
	_elapsed += delta
	_display_intensity = move_toward(
		_display_intensity,
		_intensity if _weather != "CLEAR" else 0.0,
		delta * 0.3
	)
	if _display_intensity > 0.001:
		queue_redraw()


func _draw() -> void:
	if _display_intensity <= 0.001:
		return
	if _weather == "RAIN":
		_draw_rain(150)
		_draw_splashes(32)
	elif _weather == "SNOW":
		_draw_snow(130)


func _draw_rain(max_count: int) -> void:
	var count: int = roundi(float(max_count) * _display_intensity)
	var wind_x: float = sin(deg_to_rad(_wind_direction)) * (3.0 + _wind_speed * 0.45)
	for index in range(count):
		var normalized_x: float = float((index * 97) % 1000) / 500.0 - 1.0
		var speed: float = 150.0 + float(index % 7) * 24.0
		var normalized_y: float = fmod(float(index * 53) + _elapsed * speed, _region_radius_y * 2.0) / _region_radius_y - 1.0
		if normalized_x * normalized_x + normalized_y * normalized_y > 1.0:
			continue
		var start := _region_center + Vector2(
			normalized_x * _region_radius_x,
			normalized_y * _region_radius_y
		)
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
		if cycle > 0.24:
			continue
		var angle: float = float(index * 137) * 0.11
		var distance: float = sqrt(float((index * 71) % 100) / 100.0)
		var splash_position := _region_center + Vector2(
			cos(angle) * distance * _region_radius_x,
			sin(angle) * distance * _region_radius_y
		)
		draw_arc(splash_position, 2.0 + cycle * 15.0, PI, TAU, 10, Color(0.72, 0.88, 1.0, 0.55), 1.0)


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
		draw_circle(flake_position, 1.8 + float(index % 3) * 0.7, Color(1.0, 1.0, 1.0, 0.82))
