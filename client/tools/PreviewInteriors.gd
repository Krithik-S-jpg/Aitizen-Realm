extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152,720)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(576,245)
	root.add_child(renderer)
	var tiles := {}
	for x: int in range(-12,13):
		for y: int in range(-12,13):
			tiles[Vector2i(x,y)] = {"terrain":"stone","metadata":{}}
	var floor: Array = []
	for x: int in range(-7,8):
		for y: int in range(-6,5):
			if pow(float(x)/7,2)+pow(float(y)/5,2) < 1:
				floor.append([x,y])
	var features := {"-3,-2":{"kind":"pool"}, "1,-3":{"kind":"ore","remaining":4}, "4,0":{"kind":"inscription"}, "-4,1":{"kind":"unstable"}}
	tiles[Vector2i.ZERO].metadata.cave = {"id":"preview","floor":floor,"surveyed":floor,"features":features}
	renderer.render_world(tiles,[],[],[{"id":"explorer","x":0,"y":0,"kind":"agent","avatar_id":"juniper","action":"idle","metadata":{"in_cave":true,"cave_position":[0,0],"cave_id":"preview"}}])
	renderer.set_cave_view(true)
	await create_timer(1).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/cave-cohesive-preview.png")
	renderer.set_cave_view(false)
	renderer.position = Vector2(576,-90)
	tiles.clear()
	for x: int in range(18):
		for y: int in range(18):
			tiles[Vector2i(x,y)] = {"terrain":"water","metadata":{"marine":{"depth":2+x*.5,"habitat":"kelp" if x<6 else "reef" if x<12 else "rock","landmark":"wreck" if x==10 and y==9 else "", "item":"shell","remaining":3}}}
	var creatures: Array = []
	for i: int in range(12):
		creatures.append({"id":"fish%d"%i,"x":5+i%6,"y":7+i/6,"kind":"animal","underwater":true,"metadata":{"marine":true,"species":"reef_fish"}})
	renderer.render_world(tiles,[],[],creatures)
	renderer.set_underwater_view(true)
	await create_timer(1).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/underwater-cohesive-preview.png")
	quit()
