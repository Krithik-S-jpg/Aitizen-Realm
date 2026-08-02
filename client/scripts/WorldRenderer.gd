# WorldRenderer.gd
extends TileMapLayer
class_name WorldRenderer

## Handles visual rendering of the isometric world grid in Godot.

const SOURCE_ID: int = 0

# Terrain type to tileset atlas coordinates
const TERRAIN_MAPPING: Dictionary = {
	"grass": Vector2i(0, 0),
	"dirt": Vector2i(1, 0),
	"stone": Vector2i(2, 0),
	"water": Vector2i(3, 0),
	"forest": Vector2i(4, 0),
	"sand": Vector2i(5, 0)
}

## Draws the full map on the TileMapLayer, ignoring unknown terrain types.
func render_world(tiles: Dictionary) -> void:
	clear()
	for coord in tiles:
		var tile_data = tiles[coord]
		var terrain = tile_data["terrain"]

		if TERRAIN_MAPPING.has(terrain):
			var atlas_coord = TERRAIN_MAPPING[terrain]
			set_cell(coord, SOURCE_ID, atlas_coord)
		else:
			# Ignore unknown terrain gracefully as per requirements
			pass
