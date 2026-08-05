# TerrainMapper.gd
extends Node
class_name TerrainMapper

## Centralizes the mapping of backend terrain strings to Godot Tileset coordinates.
## Avoids hardcoding coordinates or Source IDs throughout other visual systems.

const SOURCE_ID: int = 0
const FALLBACK_COORDS: Vector2i = Vector2i(0, 0) # grass default

const TERRAIN_COORDS: Dictionary = {
	"grass": Vector2i(0, 0),
	"dirt": Vector2i(1, 0),
	"stone": Vector2i(2, 0),
	"water": Vector2i(3, 0),
	"forest": Vector2i(4, 0),
	"sand": Vector2i(5, 0)
}

## Returns the appropriate atlas coordinates for a terrain string, or a default fallback if unknown.
func get_atlas_coords(terrain: String) -> Vector2i:
	var normalized = terrain.to_lower()
	if TERRAIN_COORDS.has(normalized):
		return TERRAIN_COORDS[normalized]
	return FALLBACK_COORDS

## Returns the TileSet source ID used for terrain rendering.
func get_source_id() -> int:
	return SOURCE_ID
