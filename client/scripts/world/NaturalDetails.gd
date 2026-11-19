extends RefCounted
## Decorative only: never changes terrain, collision, supplies or navigation.
const WET := ["water", "ocean", "swamp", "wetland", "ice"]
const OFFSETS := [Vector2i(0, -1), Vector2i(1, 0), Vector2i(0, 1), Vector2i(-1, 0)]

static func edge_band(canvas, a: Vector2, b: Vector2, center: Vector2, color: Color, width: float) -> void:
	var inner_a := a.lerp(center, width)
	var inner_b := b.lerp(center, width)
	canvas.draw_polygon(PackedVector2Array([a, b, inner_b, inner_a]), PackedColorArray([color, color, Color(color, 0), Color(color, 0)]))

static func ground(canvas, coordinate: Vector2i, tiles: Dictionary, diamond: PackedVector2Array, palette: Dictionary, detail: int) -> void:
	var tile: Dictionary = tiles[coordinate]
	var terrain := str(tile.get("terrain", "grass")).to_lower()
	var center := (diamond[0] + diamond[2]) * 0.5
	var seed := posmod(coordinate.x * 73 + coordinate.y * 37, 101)
	var wet := terrain in WET
	for edge: int in range(4):
		var neighbor: Dictionary = tiles.get(coordinate + OFFSETS[edge], {})
		if neighbor.is_empty():
			continue
		var other := str(neighbor.get("terrain", "grass")).to_lower()
		if other == terrain:
			continue
		if wet and other not in WET:
			# Broad translucent shallows, no bright grid-shaped shoreline outline.
			edge_band(canvas, diamond[edge], diamond[(edge + 1) % 4], center, Color(0.56, 0.68, 0.47, 0.47), 0.72)
		elif not wet:
			var tint: Color = palette.get(other, Color("76816c"))
			tint.a = 0.27 if other not in WET else 0.18
			edge_band(canvas, diamond[edge], diamond[(edge + 1) % 4], center, tint, 0.44)
	if detail < 1 or wet:
		return
	# Sparse deterministic ground cover stays cached with the terrain layer.
	if terrain in ["forest", "grass", "meadow"] and seed < 34:
		var point := center + Vector2(seed % 17 - 8, seed % 7 - 3)
		canvas.draw_line(point - Vector2(4, 1), point + Vector2(5, 2), Color(0.24, 0.29, 0.16, 0.3), 1.3)
		if detail > 1:
			canvas.draw_circle(point + Vector2(6, -2), 1.6, Color(0.56, 0.57, 0.28, 0.35))
	elif terrain in ["stone", "mountain"] and seed < 50:
		canvas.draw_line(center - Vector2(11, 1), center + Vector2(7, 4), Color(0.17, 0.22, 0.23, 0.16), 2.0)

static func shadow(canvas: CanvasItem, base: Vector2, radius: float, detail: int) -> void:
	if detail == 0:
		return
	# Shared light direction. Two translucent ellipses approximate a soft edge.
	canvas.draw_set_transform(base + Vector2(radius * 0.22, 4), -0.15, Vector2(1.0, 0.35))
	canvas.draw_circle(Vector2.ZERO, radius, Color(0.05, 0.10, 0.09, 0.09))
	canvas.draw_circle(Vector2.ZERO, radius * 0.72, Color(0.05, 0.10, 0.09, 0.12))
	canvas.draw_set_transform(Vector2.ZERO)

static func foundation(canvas: CanvasItem, base: Vector2, kind: String, detail: int) -> void:
	if detail == 0 or kind in ["bridge", "road", "farm", "campfire", "torch"]:
		return
	var footprint := PackedVector2Array([base+Vector2(-37,0),base+Vector2(0,-17),base+Vector2(37,0),base+Vector2(0,19)])
	canvas.draw_colored_polygon(footprint, Color(0.29, 0.27, 0.20, 0.28))
	# Worn doorstep, not a fictional road or resource pile.
	canvas.draw_polygon(PackedVector2Array([base+Vector2(0,9),base+Vector2(10,5),base+Vector2(25,14),base+Vector2(14,20)]), PackedColorArray([Color(0.59,0.51,0.35,0.38),Color(0.59,0.51,0.35,0.38),Color(0.59,0.51,0.35,0),Color(0.59,0.51,0.35,0)]))


class GroundBatch:
	extends RefCounted
	var vertices := PackedVector3Array()
	var colors := PackedColorArray()
	func draw_polygon(points: PackedVector2Array, tint: PackedColorArray) -> void:
		for i: int in range(1, points.size() - 1):
			for k: int in [0, i, i + 1]:
				vertices.append(Vector3(points[k].x, points[k].y, 0))
				colors.append(tint[k] if tint.size() > 1 else tint[0])
	func draw_line(a: Vector2, b: Vector2, tint: Color, width: float) -> void:
		var normal := (b - a).normalized().orthogonal() * width * 0.5
		draw_polygon(PackedVector2Array([a-normal,b-normal,b+normal,a+normal]),PackedColorArray([tint]))
	func draw_circle(center: Vector2, radius: float, tint: Color) -> void:
		var points := PackedVector2Array()
		for i: int in range(10):
			points.append(center + Vector2.from_angle(i * TAU / 10.0) * Vector2(radius, radius * 0.35))
		draw_polygon(points, PackedColorArray([tint]))
	func mesh() -> ArrayMesh:
		var result := ArrayMesh.new()
		if vertices.is_empty():
			return result
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_COLOR] = colors
		result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		return result

static func build(renderer: Node2D, coordinates: Array, tiles: Dictionary, resources: Array, palette: Dictionary, detail: int) -> ArrayMesh:
	var batch := GroundBatch.new()
	if detail == 0:
		return batch.mesh()
	for coordinate: Vector2i in coordinates:
		ground(batch, coordinate, tiles, renderer._diamond_at(renderer.map_to_local(coordinate)), palette, detail)
	for resource: Dictionary in resources:
		var kind := str(resource.get("type", ""))
		var coordinate := Vector2i(int(resource.get("x",0)),int(resource.get("y",0)))
		if kind not in ["tree", "bush", "stone"] or not renderer._is_coordinate_visible(coordinate):
			continue
		var radius := 23.0 if kind == "tree" else 10.0
		var base: Vector2 = renderer.map_to_local(coordinate) + Vector2(radius * 0.22, 4)
		batch.draw_circle(base, radius, Color(0.05,0.10,0.09,0.09))
		batch.draw_circle(base, radius * 0.72, Color(0.05,0.10,0.09,0.12))
	return batch.mesh()
