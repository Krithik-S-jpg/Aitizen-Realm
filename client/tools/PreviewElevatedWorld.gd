extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 720)
	var renderer := WorldRenderer.new()
	renderer.position = Vector2(576, -40)
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
	for at: Vector2i in tiles:
		var tier := 1 if at.y < 9+int(sin(at.x*.32)*2) else 0
		if tiles[at].terrain != "water":
			tier += 1 if at.x < 14 else 2
		tiles[at].metadata.terrace = tier
		tiles[at].metadata.ramps = []
	for at: Vector2i in tiles:
		for delta: Vector2i in [Vector2i(1,0),Vector2i(0,1)]:
			if tiles.has(at+delta) and tiles[at].terrain != "water" and tiles[at+delta].terrain != "water" and abs(tiles[at].metadata.terrace-tiles[at+delta].metadata.terrace)==1 and at.x%6==0:
				tiles[at].metadata.ramps.append([at.x+delta.x,at.y+delta.y])
				tiles[at+delta].metadata.ramps.append([at.x,at.y])
	var structures: Array = []
	for location: Vector2i in [Vector2i(16,12),Vector2i(20,12),Vector2i(20,17)]:
		structures.append({"id":str(location),"x":location.x,"y":location.y,"structure_type":"shelter","completed":true,"entrance":[location.x+1,location.y],"footprint":[[location.x,location.y],[location.x-1,location.y],[location.x,location.y-1],[location.x-1,location.y-1]]})
	structures.append({"id":"fire","x":17,"y":16,"structure_type":"campfire","completed":true,"fuel":10})
	for x: int in range(16,19):
		for y: int in range(15,18):
			tiles[Vector2i(x,y)].metadata.settlement_square = true
	for x: int in range(17,22):
		tiles[Vector2i(x,14)].metadata.settlement_path = true
	var entities: Array = []
	for i: int in range(4):
		entities.append({"id":"person%d"%i,"kind":"agent","name":"Citizen","x":15+i,"y":16+i,"avatar_id":"juniper" if i%2 else "rowan","action":"idle","metadata":{}})
	renderer.render_world(tiles,resources,structures,entities)
	renderer.configure_environment({"weather":"CLEAR","phase":"DAY","wind_speed":4.0,"wind_direction":70})
	for at: Vector2i in [Vector2i(16,12),Vector2i(20,12),Vector2i(5,5)]:
		assert(renderer.local_to_map(renderer.map_to_local(at)) == at,"Elevated tile picking must round-trip")
	await create_timer(1.0).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/elevated-world-preview.png")
	quit()
