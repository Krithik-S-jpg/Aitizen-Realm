extends SceneTree


func _initialize() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	renderer._record_visual_motion("citizen", Vector2.ZERO, Vector2(1, 0))
	assert(renderer._entity_facing["citizen"] == 1.0)
	var distance: float = renderer._entity_stride_distances["citizen"]
	assert(distance > 0.0)
	renderer._record_visual_motion("citizen", Vector2(1, 0), Vector2.ZERO)
	assert(renderer._entity_facing["citizen"] == -1.0)
	assert(is_equal_approx(renderer._entity_stride_distances["citizen"], distance * 2))
	renderer._record_visual_motion("citizen", Vector2.ZERO, Vector2.ZERO)
	assert(is_equal_approx(renderer._entity_stride_distances["citizen"], distance * 2))
	renderer._tiles = {
		Vector2i.ZERO: {"terrain": "water"},
		Vector2i(0, -1): {"terrain": "sand"},
		Vector2i(1, 0): {"terrain": "water"},
		Vector2i(0, 1): {"terrain": "grass"},
	}
	assert(renderer.shoreline_edges(Vector2i.ZERO) == [0, 2])
	renderer._entity_visual_positions["citizen"] = Vector2.ZERO
	renderer.update_entities([])
	assert(not renderer._entity_facing.has("citizen"))
	assert(not renderer._entity_stride_distances.has("citizen"))
	print("PASS: facing, distance-based gait, stationary gait, shoreline boundaries and cleanup")
	quit()
