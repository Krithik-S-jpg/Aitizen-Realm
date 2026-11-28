extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	renderer._tiles = {
		Vector2i(0,0): {"terrain":"water", "metadata":{"flow_to":[1,0]}},
		Vector2i(1,0): {"terrain":"water", "metadata":{}},
		Vector2i(0,1): {"terrain":"grass", "metadata":{}},
		Vector2i(2,0): {"terrain":"water", "metadata":{"flow_to":[3,0]}},
		Vector2i(3,0): {"terrain":"grass", "metadata":{}}
	}
	renderer._cache_water_profiles()
	assert(renderer._water_profiles[Vector2i.ZERO].flow.is_equal_approx(Vector2(32,16).normalized()), "Project downstream direction into isometric screen space")
	assert(renderer._water_profiles[Vector2i(1,0)].flow == Vector2.ZERO, "Lakes must not invent a current")
	assert(renderer._water_profiles[Vector2i(2,0)].flow == Vector2.ZERO, "Invalid land destinations must not produce flow")
	assert(not renderer._water_profiles.has(Vector2i(0,1)), "Land must never receive water animation")
	assert(renderer._water_profiles[Vector2i.ZERO].edges.has(2), "Shore wash must use the adjacent land edge")
	print("PASS: river flow projection, lake fallback, invalid outlets and shore edges")
	quit()
