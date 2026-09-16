# WorldRenderer.gd
extends Node2D
class_name WorldRenderer

## Draws the backend's logical grid as a clean low-poly isometric world.
## Terrain and objects remain backend-owned; this node only projects them.

@export var tile_width: float = 64.0
@export var tile_height: float = 32.0
@export var slab_depth: float = 10.0
@export var chunk_size: int = 16
@export var visible_chunk_radius: int = 2

const TERRAIN_COLORS: Dictionary = {
	"grass": Color("57b96c"),
	"dirt": Color("ae7950"),
	"stone": Color("89969b"),
	"water": Color("4ba2d2"),
	"forest": Color("328d55"),
	"sand": Color("d9bc73"),
	"ocean": Color("2879ad"),
	"mountain": Color("65747b"),
	"desert": Color("c98d4c"),
	"tundra": Color("c8d6d2"),
	"wetland": Color("398b68"),
	"snow": Color("e8f0ed"),
	"ice": Color("8fd8e8"),
	"meadow": Color("63c96b"),
	"swamp": Color("396f5d"),
	"savanna": Color("c7a34e"),
	"volcanic": Color("443f43")
}
const FALLBACK_COLOR := Color("7fcf72")
const LEFT_EDGE_COLOR := Color("d58b48")
const RIGHT_EDGE_COLOR := Color("9a5128")
const HOVER_COLOR := Color(1.0, 1.0, 1.0, 0.32)
const SELECTED_COLOR := Color("fff2a8")
const NO_TILE := Vector2i(2147483647, 2147483647)
const ANIMATION_FPS := 12.0

var _tiles: Dictionary = {}
var _resources: Array = []
var _structures: Array = []
var _entities: Array = []
var _active_mining: Dictionary = {}
var _simulation_running := true
var _visual_seconds := 0.0

func set_simulation_running(running: bool) -> void:
	_simulation_running = running
	if not running:
		for key: Variant in _entity_target_positions:
			_entity_visual_positions[key] = _entity_target_positions[key]
			_entity_motion_amounts[key] = 0.0
	queue_redraw()

func _visual_msec() -> int:
	return int(_visual_seconds * 1000.0)
var _hovered_tile := NO_TILE
var _selected_tile := NO_TILE
var _visible_chunk_center := Vector2i(0, 0)
var _active_layer := "terrain"
var _resource_positions: Dictionary = {}
var _population_positions: Dictionary = {}
var _entity_visual_positions: Dictionary = {}
var _entity_target_positions: Dictionary = {}
var _entity_motion_amounts: Dictionary = {}
var _sprite_atlas: Texture2D
var _agent_sprite_regions: Dictionary = {}
var _environment_atlas: Texture2D
var _resource_sprite_regions: Dictionary = {}
var _terrain_sprite_regions: Dictionary = {}
var _expansion_atlas: Texture2D
var _expansion_terrain_regions: Dictionary = {}
var _expansion_resource_regions: Dictionary = {}
var _animal_sprite_regions: Dictionary = {}
var _wildlife_atlas: Texture2D
var _wildlife_atlas_2: Texture2D
var _resource_fall_started_ms: Dictionary = {}
var _active_chops: Dictionary = {}
var _ordered_coordinates: Array[Vector2i] = []
var _ordered_resources: Array = []
var _ordered_structures: Array = []
var _ordered_entities: Array = []
var _animation_accumulator := 0.0


func _ready() -> void:
	_load_sprite_atlas_config()


func render_world(
	tiles: Dictionary,
	resources: Array = [],
	structures: Array = [],
	entities: Array = []
) -> void:
	_tiles = tiles.duplicate(true)
	_resources = resources.duplicate(true)
	_structures = structures.duplicate(true)
	update_entities(entities)
	_refresh_resource_positions()
	_rebuild_draw_order()
	queue_redraw()


func update_structures(structures: Array) -> void:
	_structures = structures.duplicate(true)
	_rebuild_draw_order()
	queue_redraw()


func update_resources(resources: Array) -> void:
	_resources = resources.duplicate(true)
	var falling_now: Dictionary = {}
	for resource: Dictionary in _resources:
		if str(resource.get("visual_state", "standing")) == "fallen":
			falling_now[str(resource.get("id", ""))] = true
	for key: Variant in _resource_fall_started_ms.keys():
		if not falling_now.has(str(key)):
			_resource_fall_started_ms.erase(key)
	_refresh_resource_positions()
	_rebuild_draw_order()
	queue_redraw()


func update_entities(entities: Array) -> void:
	_entities = entities.duplicate(true)
	_population_positions.clear()
	_active_chops.clear()
	_active_mining.clear()
	var present: Dictionary = {}
	for entity: Dictionary in _entities:
		var key := str(entity.get("id", "%s,%s" % [entity.get("x", 0), entity.get("y", 0)]))
		var target := Vector2(float(entity.get("x", 0)), float(entity.get("y", 0)))
		present[key] = true
		_entity_target_positions[key] = target
		if not _entity_visual_positions.has(key) or not _simulation_running:
			_entity_visual_positions[key] = target
		var map_position := Vector2i(roundi(target.x), roundi(target.y))
		_population_positions[map_position] = int(_population_positions.get(map_position, 0)) + 1
		if str(entity.get("action", "")).to_lower() in ["chop", "gather", "mine"]:
			var action_target_value: Variant = entity.get("action_target", {})
			if action_target_value is Dictionary:
				var resource_id := str((action_target_value as Dictionary).get("resource_id", ""))
				var progress := clampf(float(entity.get("action_progress", 0.0)), 0.0, 1.0)
				var rx := int(action_target_value.get("resource_x", -99999))
				var ry := int(action_target_value.get("resource_y", -99999))
				if not resource_id.is_empty() and progress > 0.0 and absf(target.x - rx) + absf(target.y - ry) == 1.0:
					if str(entity.get("action", "")) == "chop":
						_active_chops[resource_id] = progress
					elif str(action_target_value.get("resource_type", "")) in ["stone", "ore"]:
						_active_mining[resource_id] = progress
	for key: Variant in _entity_visual_positions.keys():
		if not present.has(key):
			_entity_visual_positions.erase(key)
			_entity_target_positions.erase(key)
	_ordered_entities = _entities.duplicate()
	_ordered_entities.sort_custom(_sort_resources)
	queue_redraw()


func _process(delta: float) -> void:
	if not _simulation_running:
		return
	_visual_seconds += delta
	_animation_accumulator += delta
	if _animation_accumulator < 0.05:
		return
	var animation_delta := _animation_accumulator
	_animation_accumulator = 0.0
	var changed := false
	for key: Variant in _entity_visual_positions:
		var current: Vector2 = _entity_visual_positions[key]
		var target: Vector2 = _entity_target_positions.get(key, current)
		var next := current.lerp(target, minf(animation_delta * 7.5, 1.0))
		_entity_motion_amounts[key] = next.distance_to(current) / maxf(animation_delta, 0.001)
		if next.distance_squared_to(current) > 0.00001:
			_entity_visual_positions[key] = next
			changed = true
	var has_active_animation := _entities.any(func(entity: Dictionary) -> bool:
		return str(entity.get("action", "idle")).to_lower() in ["move", "wander", "patrol", "regroup", "return_home", "seek_water", "forage", "flee", "chase", "hunt", "feed", "graze", "drink", "root", "chop", "gather", "pluck", "build", "craft"]
	)
	var has_falling_tree := _resource_fall_started_ms.values().any(func(started: Variant) -> bool:
		return _visual_msec() - int(started) < 900
	)
	if changed or has_active_animation or has_falling_tree:
		queue_redraw()


func set_observation_layer(layer_name: String) -> void:
	_active_layer = layer_name
	queue_redraw()


func get_entity_visual_local(entity_id: String) -> Vector2:
	var map_position: Vector2 = _entity_visual_positions.get(entity_id, Vector2.ZERO)
	if not _entity_visual_positions.has(entity_id):
		for entity: Dictionary in _entities:
			if str(entity.get("id", "")) == entity_id:
				map_position = Vector2(float(entity.get("x", 0)), float(entity.get("y", 0)))
				break
	return _map_vector_to_local(map_position)


func get_entity_at(map_position: Vector2i) -> Dictionary:
	for entity: Dictionary in _entities:
		if Vector2i(int(entity["x"]), int(entity["y"])) == map_position:
			return entity
	return {}


func get_structure_at(map_position: Vector2i) -> Dictionary:
	for structure: Dictionary in _structures:
		if Vector2i(int(structure["x"]), int(structure["y"])) == map_position:
			return structure
	return {}


func get_resource_at(map_position: Vector2i) -> Dictionary:
	for resource: Dictionary in _resources:
		if Vector2i(resource["x"], resource["y"]) == map_position:
			return resource
	return {}


func map_to_local(map_position: Vector2i) -> Vector2:
	return Vector2(
		float(map_position.x - map_position.y) * tile_width * 0.5,
		float(map_position.x + map_position.y) * tile_height * 0.5
	)


func local_to_map(local_position: Vector2) -> Vector2i:
	var map_x := local_position.x / tile_width + local_position.y / tile_height
	var map_y := local_position.y / tile_height - local_position.x / tile_width
	return Vector2i(roundi(map_x), roundi(map_y))


func set_hovered_tile(map_position: Vector2i) -> void:
	if _hovered_tile == map_position:
		return
	_hovered_tile = map_position
	queue_redraw()


func set_selected_tile(map_position: Vector2i) -> void:
	_selected_tile = map_position
	queue_redraw()


func clear_selection() -> void:
	_selected_tile = NO_TILE
	queue_redraw()


func set_visible_chunk_center(chunk_position: Vector2i) -> void:
	if _visible_chunk_center == chunk_position:
		return
	_visible_chunk_center = chunk_position
	_rebuild_draw_order()
	queue_redraw()


func get_visible_chunk_count() -> int:
	var diameter := visible_chunk_radius * 2 + 1
	return diameter * diameter


func _draw() -> void:
	if _tiles.is_empty():
		return

	for coordinate: Vector2i in _ordered_coordinates:
		if not _is_on_screen(map_to_local(coordinate), 100.0):
			continue
		_draw_tile(coordinate, _tiles[coordinate])

	for resource: Dictionary in _ordered_resources:
		var resource_position := Vector2i(resource["x"], resource["y"])
		if not _is_on_screen(map_to_local(resource_position), 150.0):
			continue
		if _draw_resource_sprite(map_to_local(resource_position), resource):
			continue
		match str(resource["type"]).to_lower():
			"tree":
				var produce_capacity: float = float(resource.get("produce_capacity", 0.0))
				var produce_ratio: float = (
					float(resource.get("produce_quantity", 0.0)) / produce_capacity
					if produce_capacity > 0.0 else 0.0
				)
				_draw_tree(
					map_to_local(resource_position),
					float(resource.get("growth", 1.0)),
					int(resource.get("variant", 0)),
					produce_ratio
				)
			"stone":
				_draw_stone(map_to_local(resource_position), float(resource.get("capacity", 100.0)), int(resource.get("variant", 0)))
			"plant":
				_draw_plant(map_to_local(resource_position), float(resource.get("growth", 1.0)), int(resource.get("variant", 0)))
			"bush":
				_draw_bush(map_to_local(resource_position), float(resource.get("growth", 1.0)), int(resource.get("variant", 0)))
			"mushroom":
				_draw_mushrooms(map_to_local(resource_position), int(resource.get("variant", 0)))
			"log":
				_draw_log(map_to_local(resource_position))
			"stump":
				_draw_stump(map_to_local(resource_position))
			"reeds":
				_draw_reeds(map_to_local(resource_position))
			"lily":
				_draw_lily(map_to_local(resource_position), int(resource.get("variant", 0)))

	for structure: Dictionary in _ordered_structures:
		var structure_position := Vector2i(int(structure["x"]), int(structure["y"]))
		if _is_on_screen(map_to_local(structure_position), 150.0):
			_draw_structure(map_to_local(structure_position), structure)

	for entity: Dictionary in _ordered_entities:
		var entity_position := Vector2i(int(entity["x"]), int(entity["y"]))
		if _is_coordinate_visible(entity_position) and _is_on_screen(map_to_local(entity_position), 150.0):
			var key := str(entity.get("id", "%s,%s" % [entity["x"], entity["y"]]))
			var visual: Vector2 = _entity_visual_positions.get(key, Vector2(entity_position))
			if str(entity.get("kind", "agent")).to_lower() == "animal":
				_draw_animal(_map_vector_to_local(visual), entity)
			else:
				_draw_agent(_map_vector_to_local(visual), entity)

	_draw_highlight(_hovered_tile, HOVER_COLOR, 1.5)
	_draw_highlight(_selected_tile, SELECTED_COLOR, 2.5)


func _draw_tile(coordinate: Vector2i, tile_data: Dictionary) -> void:
	var center := map_to_local(coordinate)
	var diamond := _diamond_at(center)
	var terrain := str(tile_data.get("terrain", "grass")).to_lower()
	var variant: int = int(tile_data.get("metadata", {}).get("variant", 0))
	var color: Color = _terrain_variant_color(TERRAIN_COLORS.get(terrain, FALLBACK_COLOR), variant)

	var used_atlas_tile := _draw_terrain_sprite(center, terrain, variant, coordinate)
	if not used_atlas_tile and not _tiles.has(coordinate + Vector2i(1, 0)):
		draw_colored_polygon(PackedVector2Array([
			diamond[1], diamond[2], diamond[2] + Vector2(0, slab_depth),
			diamond[1] + Vector2(0, slab_depth)
		]), RIGHT_EDGE_COLOR)
	if not used_atlas_tile and not _tiles.has(coordinate + Vector2i(0, 1)):
		draw_colored_polygon(PackedVector2Array([
			diamond[2], diamond[3], diamond[3] + Vector2(0, slab_depth),
			diamond[2] + Vector2(0, slab_depth)
		]), LEFT_EDGE_COLOR)

	if not used_atlas_tile:
		draw_colored_polygon(diamond, color)
	if terrain in ["water", "ocean", "wetland", "swamp", "ice"]:
		var wave_phase := float(_visual_msec()) * 0.0018 + float(coordinate.x * 3 + coordinate.y * 5)
		var wave_offset := sin(wave_phase) * 5.0
		draw_line(
			center + Vector2(-13 + wave_offset, -2),
			center + Vector2(-2 + wave_offset, -2),
			Color(0.78, 0.94, 1.0, 0.38),
			1.2
		)
	_draw_layer_overlay(coordinate, diamond, tile_data)
	if not used_atlas_tile or terrain in ["meadow", "swamp", "savanna", "volcanic"]:
		_draw_tile_details(coordinate, center, terrain, variant)
	if terrain == "mountain" and posmod(coordinate.x * 19 + coordinate.y * 23, 10) < 7:
		_draw_mountain(coordinate, center, float(tile_data.get("metadata", {}).get("elevation", 0.8)))


func _draw_terrain_sprite(center: Vector2, terrain: String, variant: int, coordinate: Vector2i) -> bool:
	if _environment_atlas == null or _terrain_sprite_regions.is_empty():
		return false
	var sprite_key := {
		"forest": "grass",
		"mountain": "stone",
		"ocean": "water",
		"wetland": "water",
		"desert": "sand",
		"tundra": "snow",
		"ice": "snow",
		"meadow": "grass",
		"swamp": "water",
		"savanna": "sand",
		"volcanic": "stone"
	}.get(terrain, terrain) as String
	if not _terrain_sprite_regions.has(sprite_key):
		return false
	var values: Array = _terrain_sprite_regions[sprite_key]
	if values.size() != 4:
		return false
	var source := Rect2(float(values[0]), float(values[1]), float(values[2]), float(values[3]))
	var biome_tints := {
		"forest": Color("d7e4de"),
		"ocean": Color("c2d9e4"),
		"mountain": Color("d7e4de"),
		"meadow": Color("d8ffcf"),
		"swamp": Color("789b78"),
		"savanna": Color("e8c47b"),
		"volcanic": Color("756d72")
	}
	var tint: Color = biome_tints.get(terrain, Color.WHITE)
	var diamond := _diamond_at(center)
	var ground: Color = TERRAIN_COLORS.get(terrain, FALLBACK_COLOR)
	# Continuous low-frequency variation, not a checkerboard of different tiles.
	var variation := sin(float(coordinate.x) * 0.19 + float(coordinate.y) * 0.13) * 0.025
	ground = ground.lightened(variation)
	draw_colored_polygon(diamond, ground)
	# Sample INSIDE the top surface: never repeat the slab walls or transparent gutter.
	var surface := PackedVector2Array([Vector2(104, 61), Vector2(162, 96), Vector2(104, 132), Vector2(47, 96)])
	var uv := PackedVector2Array()
	var shift := posmod(coordinate.x * 17 + coordinate.y * 31 + variant, 4)
	for index: int in range(4):
		uv.append((source.position + surface[(index + shift) % 4]) / _environment_atlas.get_size())
	tint.a = 0.18
	if terrain in ["snow", "tundra", "ice", "water", "ocean", "wetland", "swamp"]:
		tint.a = 0.06
	elif terrain in ["stone", "mountain"]:
		tint.a = 0.3
	draw_polygon(diamond, PackedColorArray([tint]), uv, _environment_atlas)
	return true


func _draw_layer_overlay(coordinate: Vector2i, diamond: PackedVector2Array, tile_data: Dictionary) -> void:
	var metadata: Dictionary = tile_data.get("metadata", {})
	var overlay := Color(0, 0, 0, 0)
	match _active_layer:
		"fertility":
			var fertility := clampf(float(metadata.get("fertility", 0.0)), 0.0, 1.0)
			overlay = Color(0.15, 0.95, 0.3, fertility * 0.62)
		"temperature":
			var temperature := clampf(float(metadata.get("temperature", 0.5)), 0.0, 1.0)
			overlay = Color(temperature, 0.15, 1.0 - temperature, 0.52)
		"humidity":
			var humidity := clampf(float(metadata.get("moisture", 0.5)), 0.0, 1.0)
			overlay = Color(0.1, 0.55, 1.0, humidity * 0.58)
		"resources":
			if _resource_positions.has(coordinate):
				overlay = Color(1.0, 0.72, 0.12, 0.55)
		"population":
			if _population_positions.has(coordinate):
				overlay = Color(0.2, 0.95, 0.9, minf(0.35 + float(_population_positions[coordinate]) * 0.12, 0.8))
	if overlay.a > 0.0:
		draw_colored_polygon(diamond, overlay)


func _terrain_variant_color(base_color: Color, variant: int) -> Color:
	match variant:
		1: return base_color.lightened(0.045)
		2: return base_color.darkened(0.045)
		3: return base_color.lightened(0.085)
		_: return base_color


func _draw_tile_details(coordinate: Vector2i, center: Vector2, terrain: String, variant: int) -> void:
	var detail_seed: int = posmod(coordinate.x * 37 + coordinate.y * 61, 13)
	match terrain:
		"grass", "forest":
			if detail_seed < 5:
				var blade_color := Color("168e4c") if terrain == "grass" else Color("087a43")
				for offset: Vector2 in [Vector2(-12, 3), Vector2(-7, 5), Vector2(9, 2)]:
					draw_line(center + offset, center + offset + Vector2(2, -5), blade_color, 1.2)
			if detail_seed == 7:
				var flower_colors: Array[Color] = [Color("f5d76e"), Color("ef7f91"), Color("c69af1"), Color("f4f0e6")]
				var flower_color: Color = flower_colors[variant]
				for offset: Vector2 in [Vector2(-9, 1), Vector2(4, -2), Vector2(11, 3)]:
					draw_circle(center + offset, 1.8, flower_color)
		"meadow":
			if detail_seed in [2, 7, 11]:
				var meadow_colors: Array[Color] = [Color("fff1a8"), Color("f7a6bd"), Color("b9a7ff"), Color("f5f1de")]
				for index: int in range(3):
					var offset := Vector2(-10 + index * 9, 1 + (index % 2) * 3)
					draw_circle(center + offset, 1.5, meadow_colors[(variant + index) % meadow_colors.size()])
		"dirt", "desert", "sand":
			if detail_seed < 4:
				draw_line(center + Vector2(-11, 1), center + Vector2(-4, 4), Color(0.35, 0.22, 0.12, 0.32), 1.0)
				draw_circle(center + Vector2(10, 2), 1.5, Color(0.35, 0.22, 0.12, 0.3))
		"water", "ocean":
			var wave_color := Color(0.62, 0.88, 1.0, 0.55) if terrain == "water" else Color(0.35, 0.72, 0.96, 0.48)
			draw_line(center + Vector2(-12, 1), center + Vector2(-2, -4), wave_color, 1.2)
			if detail_seed % 3 == 0:
				draw_line(center + Vector2(5, 5), center + Vector2(13, 1), wave_color, 1.0)
		"wetland":
			if detail_seed < 5:
				for offset_x: float in [-10.0, -5.0, 8.0]:
					draw_line(center + Vector2(offset_x, 5), center + Vector2(offset_x + 2, -4), Color("356c45"), 1.4)
		"swamp":
			if detail_seed < 4:
				draw_circle(center + Vector2(-7, 1), 3.0, Color("477d57"))
				draw_line(center + Vector2(8, 5), center + Vector2(10, -5), Color("294f36"), 1.4)
		"savanna":
			if detail_seed < 4:
				for offset_x: float in [-9.0, 7.0]:
					draw_line(center + Vector2(offset_x, 5), center + Vector2(offset_x + 3, -3), Color("8c6a2e"), 1.2)
		"volcanic":
			if detail_seed < 3:
				draw_polyline(PackedVector2Array([center + Vector2(-11, 1), center + Vector2(-3, -2), center + Vector2(2, 3), center + Vector2(10, -1)]), Color("d85b35"), 1.5)
		"snow":
			if detail_seed < 5:
				draw_circle(center + Vector2(-8, 1), 1.2, Color.WHITE)
				draw_circle(center + Vector2(9, -1), 1.0, Color.WHITE)
		"ice":
			if detail_seed < 7:
				draw_polyline(PackedVector2Array([center + Vector2(-10, -1), center + Vector2(-2, 2), center + Vector2(4, -3), center + Vector2(11, 1)]), Color(0.82, 0.97, 1.0, 0.75), 1.1)


func _draw_mountain(coordinate: Vector2i, tile_center: Vector2, elevation: float) -> void:
	var variation: int = posmod(coordinate.x * 17 + coordinate.y * 31, 11)
	var is_major_peak: bool = variation < 5 or elevation > 0.86
	var shadow_center := tile_center + Vector2(5, 7)
	draw_colored_polygon(PackedVector2Array([
		shadow_center + Vector2(-22, 0), shadow_center + Vector2(0, -8),
		shadow_center + Vector2(25, 0), shadow_center + Vector2(0, 10)
	]), Color(0.05, 0.09, 0.10, 0.25))

	if not is_major_peak:
		_draw_rock_peak(tile_center, 24.0, 19.0, float(variation - 5) * 1.5, false)
		return

	var height: float = 48.0 + clampf((elevation - 0.78) * 210.0, 0.0, 30.0)
	var width: float = 27.0 + float(variation % 3) * 3.0
	var lean: float = float(variation - 4) * 1.15
	_draw_rock_peak(tile_center, width, height, lean, true)

	# A smaller shoulder breaks up the repeated pyramid silhouette.
	var shoulder_side: float = -1.0 if variation % 2 == 0 else 1.0
	_draw_rock_peak(
		tile_center + Vector2(shoulder_side * 17.0, 3.0),
		16.0,
		height * 0.52,
		-lean * 0.4,
		false
	)


func _draw_rock_peak(base: Vector2, half_width: float, height: float, lean: float, snowy: bool) -> void:
	var peak := base + Vector2(lean, -height)
	var left := base + Vector2(-half_width, 5)
	var right := base + Vector2(half_width, 5)
	var foot := base + Vector2(2, 12)

	# Warm and cool faces create a readable low-poly rock mass.
	draw_colored_polygon(PackedVector2Array([peak, left, foot]), Color("87949a"))
	draw_colored_polygon(PackedVector2Array([peak, foot, right]), Color("3d4b53"))
	draw_colored_polygon(PackedVector2Array([
		peak + Vector2(-2, height * 0.34), left + Vector2(7, -2), foot
	]), Color("6d7a80"))
	draw_colored_polygon(PackedVector2Array([
		peak + Vector2(2, height * 0.43), foot, right + Vector2(-7, -1)
	]), Color("536169"))

	if snowy:
		var snow_depth: float = height * 0.27
		draw_colored_polygon(PackedVector2Array([
			peak,
			peak + Vector2(-half_width * 0.31, snow_depth),
			peak + Vector2(-3, snow_depth * 0.72),
			peak + Vector2(2, snow_depth * 1.08),
			peak + Vector2(half_width * 0.34, snow_depth)
		]), Color("edf3f2"))


func _draw_highlight(coordinate: Vector2i, color: Color, width: float) -> void:
	if not _tiles.has(coordinate):
		return
	var diamond := _diamond_at(map_to_local(coordinate))
	var outline := PackedVector2Array([diamond[0], diamond[1], diamond[2], diamond[3], diamond[0]])
	draw_polyline(outline, color, width, true)


func _draw_tree(tile_center: Vector2, growth: float, variant: int, produce_ratio: float) -> void:
	if variant == 1:
		_draw_conifer(tile_center, growth)
		return
	if variant == 2:
		_draw_deciduous_tree(tile_center, growth, produce_ratio)
		return
	var base := tile_center + Vector2(0, -tile_height * 0.15)
	var trunk_height := 8.0 + 15.0 * growth
	var crown_width := 7.0 + 11.0 * growth
	var crown_half_height := 3.0 + 5.0 * growth
	var crown_height := 9.0 + 15.0 * growth
	var trunk_top := base + Vector2(0, -trunk_height)

	# A small isometric ground shadow seats the tree on its terrain tile.
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -4), base + Vector2(9, 0),
		base + Vector2(0, 4), base + Vector2(-9, 0)
	]), Color(0.0, 0.25, 0.12, 0.42))

	# Two trunk faces make the narrow rectangular trunk read as a solid prism.
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(-5, 0), base + Vector2(0, 3),
		trunk_top + Vector2(0, 3), trunk_top + Vector2(-5, 0)
	]), Color("704124"))
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, 3), base + Vector2(5, 0),
		trunk_top + Vector2(5, 0), trunk_top + Vector2(0, 3)
	]), Color("4f2b19"))

	# The canopy is a proper isometric cube matching the project's visual reference.
	var crown_center := trunk_top + Vector2(0, -(crown_height + crown_half_height))
	var crown_top := crown_center + Vector2(0, -crown_half_height)
	var crown_right := crown_center + Vector2(crown_width, 0)
	var crown_bottom := crown_center + Vector2(0, crown_half_height)
	var crown_left := crown_center + Vector2(-crown_width, 0)
	var crown_drop := Vector2(0, crown_height)

	draw_colored_polygon(PackedVector2Array([
		crown_left, crown_bottom, crown_bottom + crown_drop, crown_left + crown_drop
	]), Color("006c34"))
	draw_colored_polygon(PackedVector2Array([
		crown_bottom, crown_right, crown_right + crown_drop, crown_bottom + crown_drop
	]), Color("008a49"))
	draw_colored_polygon(PackedVector2Array([
		crown_top, crown_right, crown_bottom, crown_left
	]), Color("239c67"))


func _draw_conifer(tile_center: Vector2, growth: float) -> void:
	var base := tile_center + Vector2(0, 4)
	var height: float = 28.0 + growth * 25.0
	draw_line(base, base + Vector2(0, -height * 0.55), Color("56351f"), 4.0)
	for layer: int in range(3):
		var layer_y: float = -height + float(layer) * height * 0.23
		var half_width: float = 10.0 + float(layer) * 5.5 + growth * 3.0
		draw_colored_polygon(PackedVector2Array([
			base + Vector2(0, layer_y),
			base + Vector2(half_width, layer_y + 18),
			base + Vector2(0, layer_y + 13),
			base + Vector2(-half_width, layer_y + 18)
		]), Color("08774b").lightened(float(layer) * 0.045))


func _draw_deciduous_tree(tile_center: Vector2, growth: float, produce_ratio: float) -> void:
	var base := tile_center + Vector2(0, 4)
	var trunk_top := base + Vector2(0, -(16.0 + growth * 14.0))
	draw_line(base, trunk_top, Color("62402a"), 5.0)
	var radius: float = 10.0 + growth * 7.0
	draw_circle(trunk_top + Vector2(-7, -4), radius * 0.75, Color("128550"))
	draw_circle(trunk_top + Vector2(8, -5), radius * 0.78, Color("0b6f43"))
	draw_circle(trunk_top + Vector2(0, -13), radius, Color("25a860"))
	var fruit_count: int = roundi(clampf(produce_ratio, 0.0, 1.0) * 7.0)
	var fruit_offsets: Array[Vector2] = [
		Vector2(-9, -12), Vector2(8, -15), Vector2(1, -23), Vector2(-13, -4),
		Vector2(13, -7), Vector2(-3, -7), Vector2(6, -3)
	]
	for index: int in range(fruit_count):
		draw_circle(trunk_top + fruit_offsets[index], 2.2, Color("e5533d"))


func _draw_stone(tile_center: Vector2, capacity: float, variant: int) -> void:
	var size: float = clampf(capacity / 140.0, 0.65, 1.35)
	var base := tile_center + Vector2(0, 2)
	var top := base + Vector2(0, -14 * size)
	var left := base + Vector2(-13 * size, -5 * size)
	var right := base + Vector2(13 * size, -5 * size)
	var bottom := base + Vector2(0, 3)
	draw_colored_polygon(PackedVector2Array([top, left, bottom]), Color("68747c"))
	draw_colored_polygon(PackedVector2Array([top, right, bottom]), Color("536069"))
	draw_colored_polygon(PackedVector2Array([
		top + Vector2(0, -5), right + Vector2(-3, -5), top, left + Vector2(3, -5)
	]), Color("aeb8bd"))
	if variant >= 2:
		var small_base := base + Vector2(12, 4)
		draw_colored_polygon(PackedVector2Array([
			small_base + Vector2(0, -8), small_base + Vector2(8, -2),
			small_base + Vector2(1, 3), small_base + Vector2(-7, -2)
		]), Color("69767d"))


func _draw_plant(tile_center: Vector2, growth: float, variant: int) -> void:
	var base := tile_center + Vector2(0, 1)
	var height := 4.0 + 9.0 * growth
	var spread := 3.0 + 6.0 * growth
	draw_line(base, base + Vector2(0, -height), Color("356b2f"), 2.0)
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -height), base + Vector2(spread, -height + 3),
		base + Vector2(0, -height + 6), base + Vector2(-spread, -height + 3)
	]), Color("65bd4f"))
	var flower_colors: Array[Color] = [Color("f3c85b"), Color("e87991"), Color("b98ce8"), Color("f2eee2")]
	draw_circle(base + Vector2(0, -height - 1), 2.2 + growth, flower_colors[variant])


func _draw_bush(tile_center: Vector2, growth: float, variant: int) -> void:
	var radius: float = 6.0 + growth * 5.0
	var base := tile_center + Vector2(0, 1)
	var bush_color := Color("2d9a4f") if variant % 2 == 0 else Color("3baa55")
	draw_circle(base + Vector2(-8, -5), radius, bush_color.darkened(0.12))
	draw_circle(base + Vector2(7, -6), radius * 0.95, bush_color.darkened(0.05))
	draw_circle(base + Vector2(0, -11), radius * 1.1, bush_color)
	if variant >= 2:
		var berry_color := Color("e45d64") if variant == 2 else Color("7259c7")
		for offset: Vector2 in [Vector2(-6, -10), Vector2(4, -14), Vector2(8, -6)]:
			draw_circle(base + offset, 1.8, berry_color)


func _draw_mushrooms(tile_center: Vector2, variant: int) -> void:
	var cap_colors: Array[Color] = [Color("dc5b45"), Color("e7a84a"), Color("b877d1"), Color("e9dfc6")]
	for offset: Vector2 in [Vector2(-8, 2), Vector2(2, -2), Vector2(9, 3)]:
		var height: float = 7.0 + float(posmod(int(offset.x) + variant, 4))
		draw_line(tile_center + offset, tile_center + offset + Vector2(0, -height), Color("e3d6b7"), 2.4)
		draw_circle(tile_center + offset + Vector2(0, -height), 4.0, cap_colors[variant])
		if variant == 0:
			draw_circle(tile_center + offset + Vector2(-1, -height - 1), 0.8, Color.WHITE)


func _draw_log(tile_center: Vector2) -> void:
	var start := tile_center + Vector2(-17, 3)
	var finish := tile_center + Vector2(15, -6)
	draw_line(start, finish, Color("70452a"), 10.0)
	draw_circle(finish, 5.2, Color("c18a55"))
	draw_circle(finish, 2.6, Color("815331"))
	draw_line(start + Vector2(8, -3), start + Vector2(4, -12), Color("4e7b3b"), 2.0)


func _draw_stump(tile_center: Vector2) -> void:
	var base := tile_center + Vector2(0, 4)
	draw_rect(Rect2(base + Vector2(-8, -12), Vector2(16, 13)), Color("70462b"))
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -17), base + Vector2(9, -12),
		base + Vector2(0, -7), base + Vector2(-9, -12)
	]), Color("c28b52"))
	draw_circle(base + Vector2(0, -12), 3.0, Color("80542f"), false, 1.2)


func _draw_reeds(tile_center: Vector2) -> void:
	for offset_x: float in [-9.0, -4.0, 1.0, 6.0, 11.0]:
		var height: float = 12.0 + fmod(abs(offset_x) * 2.0, 7.0)
		draw_line(tile_center + Vector2(offset_x, 5), tile_center + Vector2(offset_x + 2, 5 - height), Color("47783b"), 1.8)
		draw_line(tile_center + Vector2(offset_x + 2, 5 - height), tile_center + Vector2(offset_x + 5, 8 - height), Color("78a94c"), 1.5)


func _draw_lily(tile_center: Vector2, variant: int) -> void:
	var base := tile_center + Vector2(0, 2)
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -5), base + Vector2(10, 0),
		base + Vector2(2, 5), base + Vector2(-9, 1)
	]), Color("4b9c52"))
	if variant >= 1:
		var flower_color := Color("f2a8cb") if variant % 2 == 1 else Color("f3e9cc")
		draw_circle(base + Vector2(1, -4), 3.0, flower_color)


func _draw_structure(tile_center: Vector2, structure: Dictionary) -> void:
	var progress: float = float(structure.get("progress_ratio", 0.0))
	var completed: bool = bool(structure.get("completed", false))
	var base := tile_center + Vector2(0, 2)
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -7), base + Vector2(22, 1),
		base + Vector2(0, 10), base + Vector2(-22, 1)
	]), Color("8b6847"))
	if not completed:
		var beam_height: float = 8.0 + progress * 20.0
		draw_line(base + Vector2(-14, 0), base + Vector2(-14, -beam_height), Color("74482a"), 4.0)
		draw_line(base + Vector2(14, 0), base + Vector2(14, -beam_height), Color("74482a"), 4.0)
		if progress >= 0.25:
			draw_line(base + Vector2(-14, -beam_height), base + Vector2(14, -beam_height), Color("bb915c"), 4.0)
		if progress >= 0.5:
			for board: int in range(4):
				var board_y := -4.0 - board * 5.0
				draw_line(base + Vector2(-13, board_y), base + Vector2(13, board_y), Color("9d764a"), 3.0)
		if progress >= 0.75:
			draw_line(base + Vector2(-18, -beam_height), base + Vector2(0, -beam_height - 14), Color("d2ae73"), 3.0)
			draw_line(base + Vector2(0, -beam_height - 14), base + Vector2(18, -beam_height), Color("d2ae73"), 3.0)
		draw_rect(Rect2(base + Vector2(-20, 12), Vector2(40, 3)), Color("263b32"))
		draw_rect(Rect2(base + Vector2(-20, 12), Vector2(40 * clampf(progress, 0, 1), 3)), Color("dbbd80"))
		return
	# Reuse the detailed world atlas rather than UI thumbnail stand-ins.
	var kind := str(structure.get("structure_type", "shelter")).to_lower()
	if kind == "farm":
		var growth: float = float(structure.get("crop_growth", 0.0))
		var ripe: bool = float(structure.get("crop_food", 0.0)) > 0.0
		for row: int in range(3):
			for column: int in range(4):
				var sprout := base + Vector2((column - row) * 6 - 3, (column + row) * 3 - 8)
				draw_line(sprout, sprout + Vector2(0, -3 - growth * 8), Color("d7b85c") if ripe else Color("70a84c"), 2.0)
		return
	if kind in ["campfire", "torch"] and float(structure.get("fuel", 0.0)) <= 0.0:
		draw_line(base + Vector2(-9, -3), base + Vector2(9, 2), Color("55483d"), 4.0)
		draw_line(base + Vector2(-9, 2), base + Vector2(9, -3), Color("55483d"), 4.0)
		return
	var regions := {
		"storage": Rect2(639, 610, 309, 230),
		"workbench": Rect2(966, 625, 269, 213),
		"campfire": Rect2(18, 650, 142, 151),
		"fence": Rect2(329, 662, 307, 153)
	}
	if _environment_atlas != null and regions.has(kind):
		var region: Rect2 = regions[kind]
		var sprite_height := 70.0 if kind in ["storage", "workbench"] else 42.0
		var sprite_width := sprite_height * region.size.x / region.size.y
		draw_texture_rect_region(_environment_atlas, Rect2(base + Vector2(-sprite_width / 2, -sprite_height + 6), Vector2(sprite_width, sprite_height)), region)
		return

	match str(structure.get("structure_type", "shelter")).to_lower():
		"campfire":
			draw_line(base + Vector2(-10, 2), base + Vector2(10, -2), Color("55331f"), 4.0)
			draw_line(base + Vector2(-10, -2), base + Vector2(10, 2), Color("55331f"), 4.0)
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(0, -23), base + Vector2(9, -4),
				base + Vector2(0, 1), base + Vector2(-8, -5)
			]), Color("f28c28"))
		"storage":
			draw_rect(Rect2(base + Vector2(-14, -20), Vector2(28, 22)), Color("98613a"))
			draw_line(base + Vector2(-14, -9), base + Vector2(14, -9), Color("d59a57"), 3.0)
		"tent":
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(-24, 3), base + Vector2(0, -36),
				base + Vector2(24, 3), base + Vector2(0, -5)
			]), Color("d7b27a"))
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(0, -36), base + Vector2(24, 3),
				base + Vector2(0, -5)
			]), Color("a67850"))
			draw_line(base + Vector2(0, -38), base + Vector2(0, 5), Color("68442d"), 2.0)
		"workbench":
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(-22, -15), base + Vector2(13, -20),
				base + Vector2(23, -13), base + Vector2(-12, -8)
			]), Color("b77a43"))
			draw_line(base + Vector2(-14, -9), base + Vector2(-14, 4), Color("674127"), 5.0)
			draw_line(base + Vector2(16, -14), base + Vector2(16, 1), Color("674127"), 5.0)
			draw_line(base + Vector2(-4, -15), base + Vector2(7, -17), Color("8a9aa1"), 3.0)
		"well":
			draw_circle(base + Vector2(0, -4), 17.0, Color("6f7d83"))
			draw_circle(base + Vector2(0, -6), 11.0, Color("203b48"))
			draw_line(base + Vector2(-15, -5), base + Vector2(-15, -34), Color("70462b"), 4.0)
			draw_line(base + Vector2(15, -5), base + Vector2(15, -34), Color("70462b"), 4.0)
			draw_line(base + Vector2(-18, -33), base + Vector2(18, -33), Color("8f5c35"), 5.0)
		"torch":
			draw_line(base, base + Vector2(0, -31), Color("694328"), 4.0)
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(0, -45), base + Vector2(7, -31),
				base + Vector2(0, -26), base + Vector2(-7, -32)
			]), Color("f19a32"))
			draw_circle(base + Vector2(0, -35), 4.0, Color("ffd85a"))
		"fence":
			draw_line(base + Vector2(-24, -8), base + Vector2(24, -14), Color("83522e"), 5.0)
			draw_line(base + Vector2(-24, 1), base + Vector2(24, -5), Color("9d6638"), 5.0)
			draw_line(base + Vector2(-18, 5), base + Vector2(-18, -21), Color("654026"), 5.0)
			draw_line(base + Vector2(18, 0), base + Vector2(18, -25), Color("654026"), 5.0)
		_:
			var roof_peak := base + Vector2(0, -42)
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(-21, -16), roof_peak, base + Vector2(21, -16), base + Vector2(0, -5)
			]), Color("795035"))
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(-17, -16), base + Vector2(0, -5),
				base + Vector2(0, 5), base + Vector2(-17, 0)
			]), Color("b68450"))
			draw_colored_polygon(PackedVector2Array([
				base + Vector2(0, -5), base + Vector2(17, -16),
				base + Vector2(17, 0), base + Vector2(0, 5)
			]), Color("8d623e"))


func _draw_animal(tile_center: Vector2, entity: Dictionary) -> void:
	if _animal_sprite_regions.is_empty():
		return
	var metadata: Dictionary = entity.get("metadata", {})
	var species := str(metadata.get("species", "rabbit")).to_lower()
	if not _animal_sprite_regions.has(species):
		return
	var action := str(entity.get("action", metadata.get("state", "idle"))).to_lower()
	var species_animations: Dictionary = _animal_sprite_regions[species]
	var animal_atlas := _wildlife_atlas_2 if str(species_animations.get("atlas", "primary")) == "secondary" else _wildlife_atlas
	if animal_atlas == null:
		return
	var moving := action in ["move", "wander", "patrol", "regroup", "return_home", "seek_water", "forage", "flee", "chase", "hunt"]
	var has_motion := _simulation_running and float(_entity_motion_amounts.get(str(entity.get("id", "")), 0.0)) > 0.04
	if moving and not has_motion:
		action = "idle"
		moving = false
	var animation_key := action if species_animations.has(action) else ("move" if moving else "idle")
	if action == "root" and species_animations.has("graze"):
		animation_key = "graze"
	if action in ["rest", "sleep"] and species_animations.has("sleep"):
		animation_key = "sleep"
	var frames: Array = species_animations.get(animation_key, species_animations.get("idle", []))
	if frames.is_empty():
		return
	var time_seconds := _visual_seconds
	var playback_rate := 1.35 if action == "flee" else (1.15 if action == "hunt" else 1.0)
	var phase := time_seconds * playback_rate
	var frame_index := int(floor(phase * ANIMATION_FPS)) % frames.size()
	var values: Array = frames[frame_index]
	if values.size() != 4:
		return
	var source := animal_frame_region(values, str(species_animations.get("atlas", "primary")))
	var height := {
		"rabbit": 38.0, "duck": 36.0, "fox": 44.0, "goat": 50.0,
		"boar": 49.0, "wolf": 52.0, "deer": 61.0, "bear": 66.0
	}.get(species, 48.0) as float
	if action in ["sleep", "rest"]:
		height *= 0.84
	var width := height * source.size.x / maxf(source.size.y, 1.0)
	var bob := sin(phase * 2.0) * (2.6 if action == "flee" else (1.6 if moving else 0.35))
	if action in ["graze", "drink", "root", "feed"]:
		bob = abs(sin(phase * 1.7)) * 2.2
	var base := tile_center + Vector2(0, 5.0 + bob)
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(-width * 0.28, -2), base + Vector2(0, -6),
		base + Vector2(width * 0.28, -2), base + Vector2(0, 3)
	]), Color(0.0, 0.0, 0.0, 0.22))
	draw_texture_rect_region(
		animal_atlas,
		Rect2(base + Vector2(-width * 0.5, -height + 4.0), Vector2(width, height)),
		source
	)
	if action in ["graze", "drink", "root", "feed", "hunt", "sleep"]:
		var feedback_color := {
			"graze": Color("7ee0a4"), "drink": Color("70c8e8"),
			"root": Color("c58b58"), "feed": Color("e88962"),
			"hunt": Color("e88962"), "sleep": Color("a9b8d6")
		}.get(action, Color("d6e2dd")) as Color
		draw_circle(base + Vector2(0, -height - 2), 3.0 + sin(phase) * 0.6, feedback_color)


func _draw_agent(tile_center: Vector2, entity: Dictionary) -> void:
	var action := str(entity.get("action", "idle")).to_lower()
	var action_target: Dictionary = entity.get("action_target", {})
	if action in ["gather", "chop", "pluck"] and action_target.has("x") and action_target.has("y"):
		var at_interaction_tile := (
			int(entity.get("x", 0)) == int(action_target["x"])
			and int(entity.get("y", 0)) == int(action_target["y"])
		)
		if not at_interaction_tile:
			action = "move"
	if action == "gather" and str(action_target.get("resource_type", "")).to_lower() == "stone":
		action = "mine"
	var entity_key := str(entity.get("id", ""))
	if float(_entity_motion_amounts.get(entity_key, 0.0)) > 0.04:
		action = "move"
	if action == "move" and float(_entity_motion_amounts.get(entity_key, 0.0)) <= 0.04:
		action = "idle"
	var phase := _visual_seconds + float(abs(str(entity.get("id", "")).hash()) % 19)
	# Keep the walking cycle while carrying; the carry atlas has only one pose.
	var working := action in ["chop", "gather", "pluck", "mine", "build", "craft"]
	var bob := sin(phase * (1.8 if working else 0.65)) * (1.8 if working else 0.6)
	var base := tile_center + Vector2(0, 3 + bob)
	var is_player: bool = "player" in entity.get("tags", [])
	var accent := Color("5de4c1") if is_player else Color("e0b868")
	# The source sprite supplies the character; code adds only world-space feedback.
	draw_colored_polygon(PackedVector2Array([
		base + Vector2(0, -2), base + Vector2(13, 2),
		base + Vector2(0, 7), base + Vector2(-13, 2)
	]), Color(0.0, 0.0, 0.0, 0.28))
	_draw_agent_sprite(base, action, phase)
	if is_player:
		draw_arc(base + Vector2(0, -12), 18.0, 0.0, TAU, 28, Color(accent, 0.72), 1.6)
		draw_string(ThemeDB.fallback_font, base + Vector2(-42, -76), str(entity.get("name", "AITIZEN")), HORIZONTAL_ALIGNMENT_CENTER, 84, 10, Color("e8f6f1"))
	if working:
		var action_color := {
			"chop": Color("e6a25a"),
			"gather": Color("77c98d"),
			"pluck": Color("e56f75"),
			"build": Color("e7c36c"),
			"craft": Color("75b9d3"),
			"mine": Color("aeb9c0")
		}.get(action, Color("aebfc4")) as Color
		var progress: float = clampf(float(entity.get("action_progress", 0.0)), 0.0, 1.0)
		draw_rect(Rect2(base + Vector2(-17, -64), Vector2(34, 4)), Color("102027"))
		draw_rect(Rect2(base + Vector2(-16, -63), Vector2(32 * progress, 2)), action_color)


func _map_vector_to_local(map_position: Vector2) -> Vector2:
	return Vector2(
		(map_position.x - map_position.y) * tile_width * 0.5,
		(map_position.x + map_position.y) * tile_height * 0.5
	)


func _draw_agent_sprite(base: Vector2, action: String, phase: float) -> void:
	if _sprite_atlas == null or _agent_sprite_regions.is_empty():
		return
	var animation_key := action if _agent_sprite_regions.has(action) else "idle"
	var frames: Array = _agent_sprite_regions.get(animation_key, [])
	if frames.is_empty():
		return
	var frame_index := int(floor(phase * ANIMATION_FPS)) % frames.size()
	var values: Array = frames[frame_index]
	if values.size() != 4:
		return
	var source_rect := Rect2(float(values[0]), float(values[1]), float(values[2]), float(values[3]))
	var aspect := source_rect.size.x / maxf(source_rect.size.y, 1.0)
	var destination_size := Vector2(68.0 * aspect, 68.0)
	var destination := Rect2(
		base + Vector2(-destination_size.x * 0.5, -destination_size.y + 3.0),
		destination_size
	)
	draw_texture_rect_region(_sprite_atlas, destination, source_rect)


func _load_sprite_atlas_config() -> void:
	var file := FileAccess.open("res://config/sprite_atlas.json", FileAccess.READ)
	if file == null:
		return
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		return
	var config: Dictionary = parsed
	_sprite_atlas = load(str(config.get("texture", ""))) as Texture2D
	_agent_sprite_regions = config.get("agent_animations", {})
	_environment_atlas = load(str(config.get("environment_texture", ""))) as Texture2D
	_resource_sprite_regions = config.get("resource_sprites", {})
	_terrain_sprite_regions = config.get("terrain_sprites", {})
	_expansion_atlas = load(str(config.get("expansion_texture", ""))) as Texture2D
	_wildlife_atlas = load(str(config.get("wildlife_texture", ""))) as Texture2D
	_wildlife_atlas_2 = load(str(config.get("wildlife_texture_2", ""))) as Texture2D
	_expansion_terrain_regions = config.get("expansion_terrain_sprites", {})
	_expansion_resource_regions = config.get("expansion_resource_sprites", {})
	_animal_sprite_regions = config.get("animal_animations", {})


func _draw_resource_sprite(tile_center: Vector2, resource: Dictionary) -> bool:
	var resource_type := str(resource.get("type", "")).to_lower()
	if _expansion_atlas != null and _expansion_resource_regions.has(resource_type):
		var expansion_values: Array = _expansion_resource_regions[resource_type]
		if expansion_values.size() == 4:
			var expansion_source := Rect2(
				float(expansion_values[0]), float(expansion_values[1]),
				float(expansion_values[2]), float(expansion_values[3])
			)
			var expansion_height := {
				"ore": 44.0, "clay": 39.0, "cactus": 54.0, "herb": 37.0
			}.get(resource_type, 42.0) as float
			var expansion_width := expansion_height * expansion_source.size.x / maxf(expansion_source.size.y, 1.0)
			draw_texture_rect_region(
				_expansion_atlas,
				Rect2(tile_center + Vector2(-expansion_width * 0.5, -expansion_height + 7.0), Vector2(expansion_width, expansion_height)),
				expansion_source
			)
			return true
	if _environment_atlas == null or _resource_sprite_regions.is_empty():
		return false
	var sprite_key := resource_type
	var height := 42.0
	match resource_type:
		"tree":
			var growth := float(resource.get("growth", 1.0))
			var produce := float(resource.get("produce_quantity", 0.0))
			var variant := int(resource.get("variant", 0))
			var visual_state := str(resource.get("visual_state", "standing"))
			height = 82.0 + growth * 20.0
			if visual_state == "stump":
				sprite_key = "stump"
				height = 44.0
			elif visual_state == "sapling":
				sprite_key = "tree_young"
				height = 60.0
			elif produce > 0.5:
				sprite_key = "tree_fruit"
			elif growth < 0.42:
				sprite_key = "tree_young"
			elif variant == 1:
				sprite_key = "tree_conifer_mature" if growth > 0.72 else "tree_conifer"
			else:
				sprite_key = "tree_mature" if growth > 0.72 else "tree_deciduous"
		"stone":
			sprite_key = "stone_large" if float(resource.get("capacity", 0.0)) > 120.0 else "stone"
			var remaining := clampf(float(resource.get("quantity", 0.0)) / maxf(float(resource.get("capacity", 1.0)), 1.0), 0.0, 1.0)
			height = lerpf(18.0, 42.0, sqrt(remaining))
		"bush":
			sprite_key = "bush_fruit" if float(resource.get("produce_quantity", 0.0)) > 0.5 else "bush"
			height = 38.0
		"plant", "mushroom", "log", "stump":
			height = 38.0 if resource_type in ["plant", "mushroom"] else 44.0
		_:
			return false
	if not _resource_sprite_regions.has(sprite_key):
		return false
	var values: Array = _resource_sprite_regions[sprite_key]
	if values.size() != 4:
		return false
	var source := Rect2(float(values[0]), float(values[1]), float(values[2]), float(values[3]))
	var width := height * source.size.x / maxf(source.size.y, 1.0)
	var destination := Rect2(tile_center + Vector2(-width * 0.5, -height + 7.0), Vector2(width, height))
	if _active_mining.has(str(resource.get("id", ""))):
		var impact := fmod(_visual_seconds, 0.5) / 0.5
		destination.position.x += sin(impact * TAU) * (1.0 - impact) * 1.5
		for chip: int in range(4):
			var direction := Vector2.from_angle(-2.8 + chip * 0.7)
			var point := tile_center + Vector2(0, -10) + direction * impact * 19 + Vector2(0, impact * impact * 12)
			draw_circle(point, 1.5, Color(0.8, 0.83, 0.8, 1.0 - impact))
	if resource_type == "tree" and str(resource.get("visual_state", "standing")) == "fallen":
		var fall_key := str(resource.get("id", "%s,%s" % [resource.get("x", 0), resource.get("y", 0)]))
		if not _resource_fall_started_ms.has(fall_key):
			_resource_fall_started_ms[fall_key] = _visual_msec()
		var elapsed := float(_visual_msec() - int(_resource_fall_started_ms[fall_key])) * 0.001
		var fall_progress := clampf(elapsed / 0.72, 0.0, 1.0)
		var eased := 1.0 - pow(1.0 - fall_progress, 3.0)
		draw_set_transform(tile_center + Vector2(0, 7), eased * 1.42, Vector2.ONE)
		draw_texture_rect_region(
			_environment_atlas,
			Rect2(Vector2(-width * 0.5, -height), Vector2(width, height)),
			source
		)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		return true
	if resource_type == "tree" and float(resource.get("growth", 1.0)) > 0.40:
		var wind_phase := float(_visual_msec()) * 0.0016 + float(int(resource.get("x", 0)) * 3 + int(resource.get("y", 0)) * 5)
		var chop_progress := _active_chop_progress(resource)
		var impact_shake := 0.0
		if chop_progress >= 0.0:
			impact_shake = sin(float(_visual_msec()) * 0.034) * 0.035
		var sway := sin(wind_phase) * 0.012 + impact_shake
		draw_set_transform(tile_center + Vector2(0, 7), sway, Vector2.ONE)
		draw_texture_rect_region(
			_environment_atlas,
			Rect2(Vector2(-width * 0.5, -height), Vector2(width, height)),
			source
		)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		if chop_progress >= 0.0:
			var pulse: float = absf(sin(float(_visual_msec()) * 0.025))
			for chip_index: int in range(3):
				var chip_angle: float = -2.7 + float(chip_index) * 0.48
				var chip_distance: float = 10.0 + pulse * (7.0 + float(chip_index) * 2.0)
				var chip_position: Vector2 = tile_center + Vector2.from_angle(chip_angle) * chip_distance + Vector2(0, 1)
				draw_circle(chip_position, 1.4, Color("d89a57"))
			draw_arc(tile_center + Vector2(0, 3), 19.0, PI, TAU, 18, Color(0.96, 0.76, 0.34, 0.35 + pulse * 0.35), 1.5)
		return true
	draw_texture_rect_region(_environment_atlas, destination, source)
	return true


static func animal_frame_region(values: Array, atlas: String) -> Rect2:
	# v4 artwork has nonuniform row spacing; config coordinates identify logical cells.
	var rows: Array[int] = [0, 214, 414, 574, 728, 899, 1080, 1250, 1448]
	var columns: Array[int] = [0, 190, 380, 548, 736, 914, 1086]
	if atlas == "secondary":
		rows = [0, 218, 411, 574, 774, 959, 1135, 1280, 1448]
		columns = [0, 188, 365, 551, 732, 913, 1086]
	var row := clampi(int(float(values[1]) / 181.0), 0, 7)
	var column := clampi(int(float(values[0]) / 181.0), 0, 5)
	if atlas == "secondary" and row == 3 and column == 3:
		return Rect2(566, 574, 144, 200) # Upright bear; exclude the neighboring resting pose.
	return Rect2(columns[column], rows[row], columns[column + 1] - columns[column], rows[row + 1] - rows[row])


func _active_chop_progress(resource: Dictionary) -> float:
	var resource_id := str(resource.get("id", ""))
	return float(_active_chops.get(resource_id, -1.0))


func _diamond_at(center: Vector2) -> PackedVector2Array:
	return PackedVector2Array([
		center + Vector2(0, -tile_height * 0.5),
		center + Vector2(tile_width * 0.5, 0),
		center + Vector2(0, tile_height * 0.5),
		center + Vector2(-tile_width * 0.5, 0)
	])


func _sort_coordinates(a: Vector2i, b: Vector2i) -> bool:
	var a_depth := a.x + a.y
	var b_depth := b.x + b.y
	if a_depth == b_depth:
		return a.x < b.x
	return a_depth < b_depth


func _sort_resources(a: Dictionary, b: Dictionary) -> bool:
	var a_depth: int = int(a["x"]) + int(a["y"])
	var b_depth: int = int(b["x"]) + int(b["y"])
	return a_depth < b_depth


func _refresh_resource_positions() -> void:
	_resource_positions.clear()
	for resource: Dictionary in _resources:
		_resource_positions[Vector2i(int(resource["x"]), int(resource["y"]))] = true


func _rebuild_draw_order() -> void:
	_ordered_coordinates.clear()
	for coordinate: Vector2i in _tiles:
		if _is_coordinate_visible(coordinate):
			_ordered_coordinates.append(coordinate)
	_ordered_coordinates.sort_custom(_sort_coordinates)
	_ordered_resources = _resources.filter(func(resource: Dictionary) -> bool:
		return _is_coordinate_visible(Vector2i(int(resource["x"]), int(resource["y"])))
	)
	_ordered_resources.sort_custom(_sort_resources)
	_ordered_structures = _structures.filter(func(structure: Dictionary) -> bool:
		return _is_coordinate_visible(Vector2i(int(structure["x"]), int(structure["y"])))
	)
	_ordered_structures.sort_custom(_sort_resources)


func _is_on_screen(local_position: Vector2, margin: float) -> bool:
	var screen_position := get_global_transform_with_canvas() * local_position
	return Rect2(Vector2.ZERO, get_viewport_rect().size).grow(margin).has_point(screen_position)


func _is_coordinate_visible(coordinate: Vector2i) -> bool:
	var coordinate_chunk := Vector2i(
		floori(float(coordinate.x) / chunk_size),
		floori(float(coordinate.y) / chunk_size)
	)
	return (
		abs(coordinate_chunk.x - _visible_chunk_center.x) <= visible_chunk_radius
		and abs(coordinate_chunk.y - _visible_chunk_center.y) <= visible_chunk_radius
	)
