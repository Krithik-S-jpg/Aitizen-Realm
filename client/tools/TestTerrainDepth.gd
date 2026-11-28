extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	var tiles := {}
	for x: int in range(12):
		for y: int in range(12):
			tiles[Vector2i(x,y)] = {"terrain":"mountain" if x<6 else "grass","metadata":{"terrace":2 if y<6 else 1}}
	renderer.render_world(tiles,[],[],[])
	var layer = renderer._dynamic_layer
	var ridges := 0
	for i: int in range(layer._static_depth_objects.size()):
		var item: Dictionary = layer._static_depth_objects[i]
		if item.kind == "mountain":
			ridges += 1
		if i>0:
			assert(not renderer._sort_ground_objects(item,layer._static_depth_objects[i-1]),"Cached scene must already be sorted")
	assert(ridges>0,"Ridges must participate in foreground depth ordering")
	assert(layer._mountain_profiles == renderer._mountain_profiles)
	print("PASS: mountains in depth layer and stationary draw order sorted")
	quit()
