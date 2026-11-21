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
	# Low-frequency variation spans several tiles instead of per-tile noise.
	if not wet and detail > 0:
		var variation := sin(coordinate.x * .31 + sin(coordinate.y * .23)) * cos(coordinate.y * .27)
		var tint := Color(.22,.28,.15,absf(variation)*.065) if variation < 0 else Color(.78,.70,.43,variation*.065)
		canvas.draw_colored_polygon(diamond,tint)
	if wet:
		for corner: int in range(4):
			var before: Dictionary = tiles.get(coordinate + OFFSETS[posmod(corner - 1, 4)], {})
			var after: Dictionary = tiles.get(coordinate + OFFSETS[corner], {})
			if before.is_empty() or after.is_empty() or str(before.get("terrain", "")).to_lower() in WET or str(after.get("terrain", "")).to_lower() in WET:
				continue
			var tip := diamond[corner]
			var a := tip.lerp(diamond[posmod(corner - 1, 4)], 0.40)
			var b := tip.lerp(diamond[(corner + 1) % 4], 0.40)
			var tint: Color = palette.get(str(after.get("terrain", "sand")).to_lower(), Color("d9bc73"))
			tint.a = 0.35
			var previous := a
			for segment: int in range(1, 7):
				var t := float(segment) / 6.0
				var point := a * (1-t) * (1-t) + tip * 2 * t * (1-t) + b * t * t
				canvas.draw_polygon(PackedVector2Array([tip, previous, point]), PackedColorArray([tint, Color(tint,0.1), Color(tint,0.1)]))
				previous = point
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
	if terrain == "mountain" or (terrain in ["grass","stone","snow"] and OFFSETS.any(func(offset: Vector2i) -> bool: return str(tiles.get(coordinate+offset,{}).get("terrain","")).to_lower() == "mountain")):
		for j: int in range(3):
			var point := center + Vector2(-13+j*12, (seed+j)%7-3)
			canvas.draw_circle(point, 3+j, Color(.42,.42,.34,.20))
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

static func foundation(canvas, base: Vector2, kind: String, detail: int) -> void:
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
	func draw_colored_polygon(points: PackedVector2Array, tint: Color) -> void:
		draw_polygon(points, PackedColorArray([tint]))
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

static func entrance_path(start: Vector2i, roads: Dictionary, tiles: Dictionary, blocked: Dictionary) -> Array:
	var parents := {start: start}
	var pending: Array[Vector2i] = [start]
	var index := 0
	while index < pending.size() and index < 96:
		var point := pending[index]
		index += 1
		if roads.has(point):
			var route: Array = [point]
			while point != start:
				point = parents[point]
				route.push_front(point)
			return route
		for offset: Vector2i in OFFSETS:
			var next := point + offset
			if parents.has(next) or blocked.has(next) or absi(next.x-start.x)+absi(next.y-start.y) > 6:
				continue
			var tile: Dictionary = tiles.get(next, {})
			if tile.is_empty() or str(tile.get("terrain", "")).to_lower() in WET or not bool(tile.get("walkable", true)):
				continue
			parents[next] = point
			pending.append(next)
	return []

static func build(renderer: Node2D, coordinates: Array, tiles: Dictionary, resources: Array, structures: Array, palette: Dictionary, detail: int) -> ArrayMesh:
	var batch := GroundBatch.new()
	if detail == 0:
		return batch.mesh()
	for coordinate: Vector2i in coordinates:
		ground(batch, coordinate, tiles, renderer._diamond_at(renderer.map_to_local(coordinate)), palette, detail)
	var tree_cells := {}
	for resource: Dictionary in resources:
		if str(resource.get("type", "")) == "tree":
			tree_cells[Vector2i(int(resource.get("x",0)),int(resource.get("y",0)))] = true
	for resource: Dictionary in resources:
		var kind := str(resource.get("type", ""))
		var coordinate := Vector2i(int(resource.get("x",0)),int(resource.get("y",0)))
		if kind not in ["tree", "bush", "stone"] or not renderer._is_coordinate_visible(coordinate):
			continue
		var radius := 23.0 if kind == "tree" else 10.0
		var base: Vector2 = renderer.map_to_local(coordinate) + Vector2(radius * 0.22, 4)
		if kind == "tree":
			var neighbors := 0
			for offset: Vector2i in OFFSETS:
				neighbors += int(tree_cells.has(coordinate+offset))
			if neighbors < 3:
				for j: int in range(3):
					batch.draw_circle(base+Vector2(-14+j*11,5+j%2*3),3.0,Color(0.24,0.36,0.19,0.38))
			if posmod(coordinate.x*13+coordinate.y*7,11) == 0:
				batch.draw_line(base+Vector2(-14,5),base+Vector2(-4,2),Color("796b4e"),2)
		batch.draw_circle(base, radius, Color(0.05,0.10,0.09,0.09))
		batch.draw_circle(base, radius * 0.72, Color(0.05,0.10,0.09,0.12))
	var roads := {}
	var blocked := tree_cells.duplicate()
	for resource: Dictionary in resources:
		if str(resource.get("type", "")) in ["stone","ore"]:
			blocked[Vector2i(int(resource.x),int(resource.y))] = true
	for structure: Dictionary in structures:
		if str(structure.get("structure_type","")) in ["road","bridge","campfire","torch"]:
			continue
		for cell: Array in structure.get("footprint", [[int(structure.x),int(structure.y)]]):
			blocked[Vector2i(int(cell[0]),int(cell[1]))] = true
	for structure: Dictionary in structures:
		if str(structure.get("structure_type", "")) == "road" and bool(structure.get("completed",false)):
			roads[Vector2i(int(structure.get("x",0)),int(structure.get("y",0)))] = true
	# Doorways are also destinations, so a village without paved roads still
	# has continuous worn paths. Never connect through a foundation or trunk.
	for structure: Dictionary in structures:
		if bool(structure.get("completed",false)) and str(structure.get("structure_type","")) in ["shelter","tent","storage","workbench","well"]:
			var door: Array = structure.get("entrance",[int(structure.x)+1,int(structure.y)])
			roads[Vector2i(int(door[0]),int(door[1]))] = true
	for structure: Dictionary in structures:
		if not bool(structure.get("completed", false)):
			continue
		var at := Vector2i(int(structure.get("x",0)),int(structure.get("y",0)))
		if not renderer._is_coordinate_visible(at):
			continue
		var base: Vector2 = renderer.map_to_local(at) + Vector2(0,2)
		var kind := str(structure.get("structure_type", "")).to_lower()
		foundation(batch,base,kind,detail)
		if kind in ["shelter", "house", "home", "tent", "storage", "workbench", "well"]:
			# Small ornamental border, outside the actual entrance; no invented food.
			for j: int in range(4 if not blocked.has(at+Vector2i(0,1)) and kind in ["shelter","house","home"] else 0):
				var edge := base + Vector2(-32+j*5, 12+j*2)
				batch.draw_line(edge,edge+Vector2(0,-5),Color("65764b"),2)
				batch.draw_circle(edge+Vector2(0,-5),1.7,Color("c7b880"))
			var entry: Array = structure.get("entrance", [at.x+1, at.y])
			var destinations := roads.duplicate()
			destinations.erase(Vector2i(int(entry[0]),int(entry[1])))
			var route := entrance_path(Vector2i(int(entry[0]), int(entry[1])), destinations, tiles, blocked)
			var previous := base + Vector2(15,14)
			for step: Vector2i in route:
				var next: Vector2 = renderer.map_to_local(step)
				batch.draw_line(previous, next, Color(0.58,0.50,0.34,0.35), 10)
				previous = next

		if kind in ["shelter","storage","tent","workbench"]:
			batch.draw_circle(base + Vector2(6,4),34,Color(0.05,0.10,0.09,0.12))
			for i: int in range(3):
				batch.draw_line(base+Vector2(8+i*5,11+i*2),base+Vector2(13+i*5,9+i*2),Color(0.52,0.50,0.42,0.55),2)
			var stock: Dictionary = structure.get("stockpile", {}) if structure.get("stockpile") is Dictionary else {}
			var items: Dictionary = stock.get("items", {}) if stock.get("items") is Dictionary else {}
			for i: int in range(mini(4,int(float(items.get("wood",0))/5))):
				var log_at := base+Vector2(-32,4-i*3)
				batch.draw_line(log_at,log_at+Vector2(12,-5),Color("806047"),3)
	return batch.mesh()
