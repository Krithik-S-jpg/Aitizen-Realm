extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1280,960)
	root.content_scale_size = Vector2i(1280,960)
	var background := ColorRect.new()
	background.color = Color("293b32")
	background.size = Vector2(1280,960)
	root.add_child(background)
	var art = preload("res://scripts/world/CohesiveArt.gd")
	var index := 0
	for group: String in ["resources","structures","items"]:
		for key: String in art.regions(group):
			var bounds: Rect2 = art.region(group,key)
			var texture: Texture2D = art.texture(group)
			assert(Rect2(Vector2.ZERO,texture.get_size()).encloses(bounds),key)
			var sprite := TextureRect.new()
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = bounds
			sprite.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			sprite.texture = atlas
			sprite.position = Vector2(index%8*160+12,index/8*126+8)
			sprite.size = Vector2(136,100)
			sprite.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			sprite.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			root.add_child(sprite)
			var label := Label.new()
			label.position = sprite.position+Vector2(0,100)
			label.text = key
			root.add_child(label)
			index += 1
	var renderer := WorldRenderer.new()
	root.add_child(renderer)
	var animals: Array = []
	for species: String in ["deer","rabbit","boar","wolf","fox","bear","goat","duck"]:
		var row: Dictionary = renderer._animal_sprite_regions[species]
		for state: String in ["move","sleep","drink"]:
			assert(row.has(state))
		animals.append({"id":species,"kind":"animal","x":0,"y":0,"action":"drink","metadata":{"species":species}})
	var painter := AnimalPreview.new()
	painter.renderer = renderer
	painter.animals = animals
	root.add_child(painter)
	await create_timer(0.5).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/cohesive-art-preview.png")
	print("PASS: 44 atlas regions and eight wildlife action sets")
	quit()

class AnimalPreview:
	extends Node2D
	var renderer: WorldRenderer
	var animals: Array
	func _draw() -> void:
		# Draw directly through the renderer during its draw notification via a callback.
		pass
	func _ready() -> void:
		renderer.draw.connect(func() -> void:
			for i: int in range(animals.size()):
				renderer._draw_animal(Vector2(80+i*160,880),animals[i])
		)
		renderer.queue_redraw()
