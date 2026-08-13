# TerrainMapper.gd
extends Node
class_name TerrainMapper

## Centralizes the mapping of backend terrain strings to Godot Tileset coordinates.
## Avoids hardcoding coordinates or Source IDs throughout other visual systems.

var _source_id: int = 0
const FALLBACK_COORDS: Vector2i = Vector2i(0, 0) # grass default

var _terrain_coords: Dictionary = {
	"grass": Vector2i(0, 0),
	"dirt": Vector2i(1, 0),
	"stone": Vector2i(2, 0),
	"water": Vector2i(3, 0)
}

## Returns the appropriate atlas coordinates for a terrain string, or a default fallback if unknown.
func get_atlas_coords(terrain: String) -> Vector2i:
	var normalized = terrain.to_lower()
	if _terrain_coords.has(normalized):
		return _terrain_coords[normalized]
	return FALLBACK_COORDS

## Returns the TileSet source ID used for terrain rendering.
func get_source_id() -> int:
	return _source_id

## Dynamically updates the coordinates and Source ID of the grass tile based on the TileSet.
func update_grass_coords(new_source_id: int, coords: Vector2i) -> void:
	_source_id = new_source_id
	_terrain_coords["grass"] = coords
	print("TerrainMapper: Grass dynamically configured to Source ID: %d, Atlas: %s" % [_source_id, str(coords)])
