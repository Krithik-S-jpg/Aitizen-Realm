# WorldRenderer.gd
extends TileMap
class_name WorldRenderer

## Translates registered tile matrices into coordinates mapping onto the isometric TileMap.

@export var mapper: TerrainMapper

func _ready() -> void:
	if not mapper:
		if has_node("TerrainMapper"):
			mapper = get_node("TerrainMapper") as TerrainMapper
		else:
			mapper = TerrainMapper.new()
			add_child(mapper)

## Populates cells on Layer 0 matching coordinate maps and terrain indices.
func render_world(tiles: Dictionary) -> void:
	clear()
	var source_id = mapper.get_source_id()

	for coord in tiles:
		var tile_data = tiles[coord]
		var terrain = tile_data["terrain"]
		var atlas_coord = mapper.get_atlas_coords(terrain)

		set_cell(0, coord, source_id, atlas_coord)
