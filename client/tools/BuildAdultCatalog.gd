extends SceneTree

func _initialize() -> void:
	var catalog := {}
	var rows := {"adult_male": [0,233,464,699,892,1067,1254], "adult_female": [0,213,422,634,833,1034,1254]}
	for avatar: String in rows:
		var path := "res://assets/pixel_art/citizens/%s_actions_v1.png" % avatar
		var pixels := Image.load_from_file(path)
		assert(pixels.get_size() == Vector2i(1254,1254))
		var actions := {}
		var names := ["move", "idle", "carry", "build", "sleep", "gather"]
		for row: int in range(6):
			var top: int = rows[avatar][row+1]
			var bottom: int = rows[avatar][row]
			for y: int in range(rows[avatar][row],rows[avatar][row+1]):
				for x: int in range(pixels.get_width()):
					if pixels.get_pixel(x,y).a > .2:
						top = mini(top,y)
						bottom = maxi(bottom,y)
			var frames: Array = []
			for column: int in range(8):
				var left := roundi(column * pixels.get_width() / 8.0)
				var right := roundi((column+1) * pixels.get_width() / 8.0)
				var foot := top
				for y: int in range(top,bottom+1):
					for x: int in range(left,right):
						if pixels.get_pixel(x,y).a > .2:
							foot = maxi(foot,y)
				# Keep horizontal pivots and scale fixed; align the planted foot.
				frames.append([left,top,right-left,foot-top+1,-(right-left)/2.0])
			actions[names[row]] = frames
		catalog[avatar] = {"texture":path,"scale":48.0/float(actions.idle[0][3]),"actions":actions}
	var output := FileAccess.open("res://config/citizen_adult_actions.json",FileAccess.WRITE)
	output.store_string(JSON.stringify(catalog,"\t"))
	print("Built adult frame catalog with shared row pivots")
	quit()
