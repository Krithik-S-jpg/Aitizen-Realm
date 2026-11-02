extends SceneTree

# Read-only connected-component audit of generated art. Never edits source pixels.
func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var path := args[0] if not args.is_empty() else "res://assets/pixel_art/citizens/scout_human_v2.png"
	var image := Image.load_from_file(path)
	assert(image != null)
	assert(image.get_pixel(0, 0).a == 0, "Atlas must be transparent")
	var width := image.get_width()
	var height := image.get_height()
	var visited := PackedByteArray()
	visited.resize(width * height)
	var rectangles: Array = []
	var labels := PackedInt32Array()
	labels.resize(width * height)
	var sizes: Array[int] = [0]
	for y in range(height):
		for x in range(width):
			var index := y * width + x
			if visited[index] or image.get_pixel(x, y).a < 0.1:
				continue
			var queue: Array[Vector2i] = [Vector2i(x, y)]
			visited[index] = 1
			var head := 0
			var bounds := Rect2i(x, y, 1, 1)
			while head < queue.size():
				var point := queue[head]
				head += 1
				bounds = bounds.merge(Rect2i(point, Vector2i.ONE))
				for delta in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
					var next: Vector2i = point + delta
					if next.x < 0 or next.y < 0 or next.x >= width or next.y >= height:
						continue
					var at := next.y * width + next.x
					if not visited[at] and image.get_pixelv(next).a >= 0.1:
						visited[at] = 1
						queue.append(next)
			if queue.size() > 500:
				rectangles.append([bounds.position.x, bounds.position.y, bounds.size.x, bounds.size.y, queue.size()])
				for point in queue:
					labels[point.y * width + point.x] = sizes.size()
				sizes.append(queue.size())
	for i in range(rectangles.size()):
		var r: Array = rectangles[i]
		var foreign := 0
		for y in range(r[1], r[1] + r[3]):
			for x in range(r[0], r[0] + r[2]):
				var label := labels[y * width + x]
				if label != 0 and label != i + 1:
					foreign += 1
		r.append(foreign)
	print(JSON.stringify(rectangles))
	quit()
