# World.gd
extends Node2D
class_name WorldView

## Handles the orchestration of world data drawing inside the World Node.

@onready var renderer: WorldRenderer = $WorldRenderer
@onready var weather_overlay: Node2D = $WeatherOverlay
var _birds: Node2D


func _ready() -> void:
	weather_overlay.renderer = renderer
	_birds = preload("res://scripts/world/AmbientBirds.gd").new()
	_birds.renderer = renderer
	_birds.z_index = 40
	add_child(_birds)

## Triggers low-poly visual rendering of the parsed backend world.
func render_parsed_world(parsed_world: Dictionary) -> void:
	renderer.chunk_size = int(parsed_world.get("chunk_size", 16))
	renderer.render_world(
		parsed_world["tiles"],
		parsed_world.get("resources", []),
		parsed_world.get("structures", []),
		parsed_world.get("entities", [])
	)
	_birds.rebuild_habitats(parsed_world["tiles"])
	# Backend birds replace decorative flocks once habitat simulation is present.
	for entity: Dictionary in parsed_world.get("entities", []):
		if entity.get("metadata", {}).get("species", "") == "songbird":
			_birds.target_activity = 0.0
			_birds.activity = 0.0
			_birds.set_meta("simulated_birds", true)


func configure_weather(calendar: Dictionary, world_width: int, world_height: int) -> void:
	_birds.configure(calendar)
	if _birds.has_meta("simulated_birds"):
		_birds.target_activity = 0.0
	renderer.configure_environment(calendar)
	var center_map := Vector2i(
		roundi(float(world_width - 1) * float(calendar.get("precipitation_center_x", 0.5))),
		roundi(float(world_height - 1) * float(calendar.get("precipitation_center_y", 0.5)))
	)
	weather_overlay.call(
		"configure",
		str(calendar.get("weather", "CLEAR")),
		float(calendar.get("weather_intensity", 0.0)),
		float(calendar.get("wind_speed", 4.0)),
		float(calendar.get("wind_direction", 0.0)),
		renderer.map_to_local(center_map),
		int(calendar.get("precipitation_radius", 10)),
		renderer.tile_width,
		renderer.tile_height
	)


func set_simulation_running(running: bool) -> void:
	renderer.set_simulation_running(running)
	weather_overlay.set_simulation_running(running)
	_birds.running = running


func set_visual_quality(quality: String) -> void:
	renderer.set_visual_quality(quality)
	weather_overlay.set_visual_quality(quality)
	_birds.quality = {"performance": .34, "balanced": .67, "high": 1.0}.get(quality.to_lower(), 1.0)
