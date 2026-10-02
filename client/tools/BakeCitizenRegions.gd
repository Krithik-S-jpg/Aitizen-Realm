extends SceneTree

# Read-only image analysis: write source-rectangle metadata, never alter pixels.
func _initialize() -> void:
	var catalog := {}
	for id: String in ["scout", "builder", "herbalist", "scholar", "cook", "miner", "fisher", "artisan"]:
		var path := "res://assets/pixel_art/citizens/%s_actions_v1.png" % id
		var pixels := Image.load_from_file(path)
		var rows: Array[Vector2i] = []
		var start := -1
		for y: int in range(pixels.get_height()):
			var opaque := false
			for x: int in range(pixels.get_width()):
				if pixels.get_pixel(x, y).a > 0.1:
					opaque = true
					break
			if opaque and start < 0:
				start = y
			elif not opaque and start >= 0:
				if y - start > 15:
					rows.append(Vector2i(start, y))
				start = -1
		if start >= 0:
			rows.append(Vector2i(start, pixels.get_height()))
		var names := ["move", "chop", "mine", "gather", "carry", "build", "sleep", "idle"]
		if id == "cook":
			names.erase("gather")
		var actions := {}
		for row: int in range(names.size()):
			var frames := []
			for column: int in range(6):
				var left := floori(column * pixels.get_width() / 6.0)
				var right := floori((column + 1) * pixels.get_width() / 6.0)
				var top := _separator(pixels, left, right, row, names.size())
				var bottom := _separator(pixels, left, right, row + 1, names.size())
				var region := Rect2i(left, top, right - left, bottom - top)
				var cropped := pixels.get_region(region)
				var used := _main_component(cropped)
				frames.append([left + used.position.x, region.position.y + used.position.y, used.size.x, used.size.y, used.position.x - (right - left) / 2.0])
			actions[names[row]] = frames
		catalog[id] = {"texture": path, "actions": actions, "scale": 68.0 / float(actions["idle"][0][3])}
		print("BAKED ", id, ": ", names.size(), " complete action rows")
	var gather_path := "res://assets/pixel_art/citizens/cook_gather_v1.png"
	var gather := Image.load_from_file(gather_path)
	var gather_frames := []
	for index: int in range(6):
		var cell := Vector2i(gather.get_width() / 3, gather.get_height() / 2)
		var origin := Vector2i(index % 3, index / 3) * cell
		var used := gather.get_region(Rect2i(origin, cell)).get_used_rect()
		gather_frames.append([origin.x + used.position.x, origin.y + used.position.y, used.size.x, used.size.y, used.position.x - cell.x / 2.0])
	catalog["cook"]["actions"]["gather"] = gather_frames
	catalog["cook"]["gather_texture"] = gather_path
	catalog["cook"]["gather_scale"] = 68.0 / float(gather_frames[3][3])
	var output := FileAccess.open("res://config/citizen_actions.json", FileAccess.WRITE)
	output.store_string(JSON.stringify(catalog, "\t"))
	quit()

func _separator(pixels: Image, left: int, right: int, row: int, count: int) -> int:
	if row == 0:
		return 0
	if row == count:
		return pixels.get_height()
	var expected := roundi(float(row) * pixels.get_height() / count)
	var best := expected
	var best_score := INF
	for y: int in range(expected - 80, expected + 81):
		var occupied := 0
		for x: int in range(left, right):
			if pixels.get_pixel(x, y).a > 0.05:
				occupied += 1
		var score := occupied * 1000.0 + absi(y - expected)
		if score < best_score:
			best_score = score
			best = y
	assert(best_score < 1000, "No transparent frame separator: manual review required")
	return best

func _main_component(pixels: Image) -> Rect2i:
	# A neighboring tool can protrude across a nominal column boundary.
	# Select the connected character silhouette, rather than including stray fragments.
	var mask := BitMap.new()
	mask.create_from_image_alpha(pixels, 0.05)
	var best := Rect2i()
	for polygon: PackedVector2Array in mask.opaque_to_polygons(Rect2i(Vector2i.ZERO, pixels.get_size()), 0.1):
		var bounds := Rect2(polygon[0], Vector2.ZERO)
		for point: Vector2 in polygon:
			bounds = bounds.expand(point)
		var candidate := Rect2i(bounds)
		if candidate.get_area() > best.get_area():
			best = candidate
	return best.grow(1).intersection(Rect2i(Vector2i.ZERO, pixels.get_size()))
