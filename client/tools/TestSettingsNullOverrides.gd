extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var panel := SimulationSettingsPanel.new()
	root.add_child(panel)
	panel.display_environment({
		"control": {
			"ticks_per_day": 24,
			"day_start_hour": 8,
			"night_start_hour": 20,
			"season_override": null,
			"weather_override": null,
			"weather_intensity_override": null,
			"temperature_override_c": null,
			"wind_speed_override": null,
			"wind_direction_override": null,
			"precipitation_radius_override": null
		},
		"calendar": {
			"hour": 11,
			"weather_intensity": 0.42,
			"temperature_c": 16.5,
			"wind_speed": 5.25,
			"wind_direction": 270.0,
			"precipitation_radius": 18
		}
	})
	assert(panel._season.selected == 0)
	assert(panel._weather.selected == 0)
	assert(is_equal_approx(panel._weather_intensity.value, 0.4))
	assert(panel._auto_temperature.button_pressed)
	assert(is_equal_approx(panel._temperature.value, 16.5))
	assert(panel._auto_wind.button_pressed)
	assert(is_equal_approx(panel._wind_speed.value, 5.5))
	assert(is_equal_approx(panel._wind_direction.value, 270.0))
	assert(is_equal_approx(panel._precipitation_radius.value, 18.0))
	# Invalid optional values also fall back instead of crashing the UI.
	panel.display_environment({"control": {"temperature_override_c": "bad"}, "calendar": {}})
	assert(is_equal_approx(panel._temperature.value, 18.0))
	print("PASS: nullable environment overrides use live calendar fallbacks")
	quit()
