extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	var tiles := {}
	for x in range(8):
		for y in range(8):
			tiles[Vector2i(x,y)] = {"terrain":"grass","metadata":{"terrace":1 if x<4 else 0}}
	renderer.render_world(tiles,[],[],[])
	var layer = renderer._dynamic_layer
	var records: Array[Dictionary] = layer._static_depth_objects
	layer._sync_depth_items(records)
	assert(not layer._depth_items.is_empty())
	var first = layer._depth_items.values()[0]
	layer._sync_depth_items(records)
	assert(first == layer._depth_items.values()[0],"Unchanged scenery must reuse its CanvasItem")
	layer._sync_depth_items([])
	assert(not first.visible,"Off-screen cached scenery must be hidden")
	layer._sync_depth_items(records)
	assert(first.visible,"Returning scenery must become visible again")
	layer._rebuild_draw_order()
	assert(layer._depth_items.is_empty(),"World changes must invalidate retained commands")
	print("PASS: retained nodes reused, visibility restored, world changes invalidate cache")
	quit()
