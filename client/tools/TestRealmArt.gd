extends SceneTree
func _initialize() -> void:
	var catalog: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://config/cohesive_art.json"))
	var count := 0
	for group: String in catalog:
		var texture := load("res://assets/world/cohesive/"+group+".png") as Texture2D
		assert(texture != null)
		for key: String in catalog[group]:
			var bounds: Array = catalog[group][key]
			assert(bounds.size()==4)
			assert(bounds[0]>=0 and bounds[1]>=0 and bounds[2]>0 and bounds[3]>0)
			assert(bounds[0]+bounds[2]<=texture.get_width() and bounds[1]+bounds[3]<=texture.get_height(),group+":"+key)
			count += 1
	var kit := (load("res://assets/world/cohesive/terrain-kit-v2.png") as Texture2D).get_image()
	assert(kit.get_pixel(0,0).a == 0)
	assert(kit.get_width()%3 == 0 and kit.get_height()%2 == 0)
	print("PASS: %d atlas regions and terrain-kit transparency"%count)
	quit()
