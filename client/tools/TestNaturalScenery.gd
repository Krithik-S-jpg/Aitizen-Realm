extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	var tiles := {}
	for x: int in range(8):
		for y: int in range(8):
			tiles[Vector2i(x,y)] = {"terrain": "water" if x < 3 else "grass", "metadata": {}}
	renderer.render_world(tiles, [{"id":"tree","x":4,"y":4,"type":"tree"}], [], [])
	assert(renderer._blended_ground_color(Vector2i(2,3), 1).is_equal_approx(renderer._blended_ground_color(Vector2i(3,3), 0)), "Adjacent ground vertices must share a tint")
	assert(renderer._scenery_mesh.mesh.get_surface_count() == 1)
	var original_mesh: ArrayMesh = renderer._scenery_mesh.mesh
	renderer.update_entities([])
	assert(renderer._scenery_mesh.mesh == original_mesh, "Citizen updates must not rebuild scenery")
	renderer.set_cave_view(true)
	assert(not renderer._scenery_mesh.visible)
	renderer.set_cave_view(false)
	assert(renderer._scenery_mesh.visible)
	renderer.set_underwater_view(true)
	assert(not renderer._scenery_mesh.visible)
	renderer.set_underwater_view(false)
	renderer.set_visual_quality("performance")
	assert(renderer._scenery_mesh.mesh.get_surface_count() == 0)
	renderer.set_visual_quality("balanced")
	assert(renderer._scenery_mesh.mesh.get_surface_count() == 1)
	renderer.update_resources([])
	assert(renderer._scenery_mesh.mesh != original_mesh)
	var home := {"id":"home","x":4,"y":5,"structure_type":"shelter","completed":true,"stockpile":{"items":{"wood":20}}}
	renderer.update_structures([home])
	var furnished: ArrayMesh = renderer._scenery_mesh.mesh
	renderer.update_structures([home])
	assert(renderer._scenery_mesh.mesh == furnished, "Unchanged buildings must reuse scenery")
	home.stockpile.items.wood = 0
	renderer.update_structures([home])
	assert(renderer._scenery_mesh.mesh != furnished, "Stockpile changes must invalidate visual piles")
	print("PASS: cached scenery, layer isolation, quality controls, resource invalidation")
	quit()
