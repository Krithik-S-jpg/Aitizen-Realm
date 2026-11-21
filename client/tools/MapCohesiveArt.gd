extends SceneTree
## Read-only pixel inspection produces sprite bounds; original artwork is untouched.
func _initialize() -> void:
	var sets := {
		"interiors": [4,4,["wall","stalagmite","vein","crystal","pool","ruin","inscription","supplies","coral","kelp","shellfish","columns","wreck","sea_arch","seagrass","entrance"]],
		"resources": [4,4,["tree_young","tree_deciduous","tree_mature","tree_conifer","tree_conifer_mature","tree_fruit","stone","stone_large","plant","bush","bush_fruit","mushroom","log","stump","ore","clay"]],
		"structures": [4,3,["shelter","tent","storage","campfire","workbench","well","farm","fence","furnace","bridge","boat","fishing_rack"]],
		"items": [4,4,["wood","stone","ore","clay","fruit","fish","bread","cooked_meat","axe","pickaxe","hammer","fishing_rod","fiber","planks","iron","waterskin"]]
	}
	var output := {}
	for key: String in sets:
		var spec: Array = sets[key]
		var image := Image.load_from_file("res://assets/world/cohesive/"+key+".png")
		assert(image != null)
		var entries := {}
		for i: int in range(spec[2].size()):
			var left := int(float(i%spec[0])*image.get_width()/spec[0])
			var top := int(float(i/spec[0])*image.get_height()/spec[1])
			var right := int(float(i%spec[0]+1)*image.get_width()/spec[0])
			var bottom := int(float(i/spec[0]+1)*image.get_height()/spec[1])
			var lo := Vector2i(right,bottom)
			var hi := Vector2i(left,top)
			for y: int in range(top,bottom):
				for x: int in range(left,right):
					if image.get_pixel(x,y).a > 0.15:
						lo = lo.min(Vector2i(x,y))
						hi = hi.max(Vector2i(x,y))
			assert(hi.x > lo.x and hi.y > lo.y)
			entries[spec[2][i]] = [lo.x,lo.y,hi.x-lo.x+1,hi.y-lo.y+1]
		output[key] = entries
	FileAccess.open("res://config/cohesive_art.json",FileAccess.WRITE).store_string(JSON.stringify(output,"  "))
	print("PASS: mapped 44 sprites without modifying source pixels")
	quit()
