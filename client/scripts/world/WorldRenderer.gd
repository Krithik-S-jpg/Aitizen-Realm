# WorldRenderer.gd
extends TileMapLayer
class_name WorldRenderer

## Translates registered tile matrices into coordinates mapping onto the isometric TileMapLayer.

@export var mapper: TerrainMapper

func _ready() -> void:
	if not mapper:
		if has_node("TerrainMapper"):
			mapper = get_node("TerrainMapper") as TerrainMapper
		else:
			mapper = TerrainMapper.new()
			add_child(mapper)

## Populates cells matching coordinate maps and terrain indices.
func render_world(tiles: Dictionary) -> void:
	# 1. Debug Checklist 1: Verify the runtime structure and print the type
	print("--- Debug Checklist 1 ---")
	print("Runtime type of tiles passed into render_world(): ", "Dictionary" if typeof(tiles) == TYPE_DICTIONARY else "Array" if typeof(tiles) == TYPE_ARRAY else str(typeof(tiles)))
	print("-------------------------")

	# 2. Validation checks
	if not tile_set:
		push_error("WorldRenderer Error: TileSet is missing on the TileMapLayer node.")
		return

	clear()

	var source_id = mapper.get_source_id()
	if not tile_set.has_source(source_id):
		push_error("WorldRenderer Error: Configured Source ID %d does not exist in the TileSet." % source_id)
		return

	var tiles_received: int = tiles.size()
	var tiles_attempted: int = 0
	var tiles_mapped: int = 0
	var tiles_placed: int = 0
	var unknown_terrain: int = 0
	var tiles_failed: int = 0

	# Try placing a single test tile first as per Step 4
	print("=== Renderer Test Started (Step 4) ===")
	var test_coord = Vector2i(0, 0)
	var test_atlas = mapper.get_atlas_coords("grass")
	set_cell(test_coord, source_id, test_atlas)

	var cell_source = get_cell_source_id(test_coord)
	var cell_atlas = get_cell_atlas_coords(test_coord)
	if cell_source == source_id and cell_atlas == test_atlas:
		print("Test tile placed successfully at (0, 0)")
	else:
		push_error("WorldRenderer Error: Placement validation failed for test tile.")
	print("=============================")

	# Clear test cell before performing full render loop
	clear()

	# 3. Step 5 & 6: Full rendering loop of backend tiles
	for coord in tiles:
		tiles_attempted += 1
		var tile_data = tiles[coord]
		var terrain = tile_data.get("terrain", "")

		# Resolve terrain
		var atlas_coord = mapper.get_atlas_coords(terrain)
		if atlas_coord == mapper.FALLBACK_COORDS and terrain != "grass":
			unknown_terrain += 1
			push_warning("WorldRenderer Warning: Unmapped terrain type '%s' at (%d, %d), falling back." % [terrain, coord.x, coord.y])
		else:
			tiles_mapped += 1

		set_cell(coord, source_id, atlas_coord)

		# Verify placement programmatically
		if get_cell_source_id(coord) == source_id and get_cell_atlas_coords(coord) == atlas_coord:
			tiles_placed += 1
		else:
			tiles_failed += 1
			push_error("WorldRenderer Error: Failed to place tile at (%d, %d)." % [coord.x, coord.y])

	# 4. Debug Checklist 7: Print mandated debug metrics
	print("--- Debug Checklist 7 ---")
	print("Received tiles: %d" % tiles_received)
	print("Rendered tiles: %d" % tiles_placed)
	print("Source ID: %d" % source_id)
	print("Atlas coords: %s" % str(test_atlas))
	if tiles.size() > 0:
		var first_key = tiles.keys()[0]
		print("First tile position: %s" % str(first_key))
	print("-------------------------")

	# Print Render Report (Step 10)
	print("=== Aitizen Realm Render Report ===")
	print("Backend tiles received: %d" % tiles_received)
	print("Tiles attempted: %d" % tiles_attempted)
	print("Tiles successfully mapped: %d" % tiles_mapped)
	print("Tiles successfully placed: %d" % tiles_placed)
	print("Unknown terrain count: %d" % unknown_terrain)
	print("Failed tile count: %d" % tiles_failed)
	print("===================================")
