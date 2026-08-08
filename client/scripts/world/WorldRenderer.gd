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

	# Dynamically discover TileSet properties to prevent hardcoding assumptions (Requirement 4)
	if tile_set:
		var source_count = tile_set.get_source_count()
		if source_count > 0:
			var active_source_id = tile_set.get_source_id(0)
			var source = tile_set.get_source(active_source_id)
			if source is TileSetAtlasSource:
				var atlas_source = source as TileSetAtlasSource
				if atlas_source.get_tiles_count() > 0:
					# Read the first tile in the atlas correctly from the TileSet
					var discovered_grass_coords = atlas_source.get_tile_id(0)
					print("TileSet Discovery: Grass tile atlas coordinates in editor are %s" % str(discovered_grass_coords))
					# Update TerrainMapper grass coordinates dynamically
					mapper.update_grass_coords(active_source_id, discovered_grass_coords)

## Populates cells matching coordinate maps and terrain indices.
func render_world(tiles: Dictionary) -> void:
	# 1. Validation checks
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

	# 2. Render backend tiles
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

	# Print Render Report (Step 10)
	print("=== Aitizen Realm Render Report ===")
	print("Backend tiles received: %d" % tiles_received)
	print("Tiles attempted: %d" % tiles_attempted)
	print("Tiles successfully mapped: %d" % tiles_mapped)
	print("Tiles successfully placed: %d" % tiles_placed)
	print("Unknown terrain count: %d" % unknown_terrain)
	print("Failed tile count: %d" % tiles_failed)
	print("===================================")
