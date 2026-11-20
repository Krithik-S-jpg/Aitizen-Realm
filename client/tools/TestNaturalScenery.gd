extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	var behind := {"base": Vector2(0, 10), "data": {"id": "citizen"}}
	var roof := {"base": Vector2(0, 20), "data": {"id": "home"}}
	var front := {"base": Vector2(0, 30), "data": {"id": "tree"}}
	assert(renderer._sort_ground_objects(behind, roof), "Citizen behind a house must render before its roof")
	assert(renderer._sort_ground_objects(roof, front), "Foreground trees must occlude buildings")
	assert(not renderer._sort_ground_objects(front, roof))
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
	var citizens := [{"id":"one","x":4,"y":4,"kind":"agent"},{"id":"two","x":4,"y":4,"kind":"agent"}]
	renderer.update_entities(citizens)
	var dynamic = renderer._dynamic_layer
	assert(dynamic._crowd_targets.size() == 2)
	assert(dynamic._crowd_targets.one != dynamic._crowd_targets.two)
	dynamic._process(0.1)
	assert(dynamic._crowd_offsets.one.length() < dynamic._crowd_targets.one.length(), "Separation must ease in")
	assert(renderer.get_entity_visual_local("one") != renderer.get_entity_visual_local("two"))
	citizens[1]["indoors"] = true
	citizens[1]["sleep_home_position"] = [4,5]
	renderer.update_entities(citizens)
	assert(dynamic._crowd_targets.is_empty())
	assert(dynamic._occupied_homes.has(Vector2i(4,5)))
	print("PASS: cached scenery, layer isolation, quality controls, resource invalidation")
	quit()
