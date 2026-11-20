extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(260, -65)
	root.add_child(renderer)
	var tiles := {}
	var resources: Array = []
	for x: int in range(28):
		for y: int in range(28):
			var river := 10 + int(sin(y * 0.23) * 2.0)
			var terrain := "grass"
			if x >= river and x <= river + 2:
				terrain = "water"
			elif x == river - 1 or x == river + 3:
				terrain = "sand"
			elif x > 19 and y < 9:
				terrain = "mountain"
			elif x < 7:
				terrain = "forest"
			tiles[Vector2i(x,y)] = {"terrain":terrain,"metadata":{"elevation":0.82,"variant":(x+y)%4}}
			if terrain == "forest" and (x * 13 + y * 7) % 7 == 0:
				resources.append({"id":"tree-%d-%d"%[x,y],"x":x,"y":y,"type":"tree","growth":0.5+float(y%5)*0.1,"variant":y%3})
	resources.append({"id":"scale-tree","x":19,"y":9,"type":"tree","growth":1.0,"variant":0})
	var structures: Array = []
	for i: int in range(3):
		structures.append({"id":"home%d"%i,"x":16+i*2,"y":12+i,"structure_type":"shelter","completed":true})
	structures.append({"id":"fire","x":17,"y":16,"structure_type":"campfire","completed":true,"fuel":10})
	var entities: Array = []
	for i: int in range(4):
		entities.append({"id":"person%d"%i,"kind":"agent","name":"Citizen","x":15+i,"y":16+i,"avatar_id":"juniper" if i%2 else "rowan","action":"idle","metadata":{}})
	renderer.render_world(tiles,resources,structures,entities)
	renderer.configure_environment({"weather":"CLEAR","phase":"DAY","wind_speed":4.0,"wind_direction":70})
	await create_timer(1.0).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/mountain-scale-preview.png")
	quit()
