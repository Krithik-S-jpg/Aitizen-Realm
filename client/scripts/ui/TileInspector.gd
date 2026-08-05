# TileInspector.gd
extends Control
class_name TileInspector

## Floating UI inspector overlay showing metrics of clicked grid cells.

@onready var panel: PanelContainer = $PanelContainer
@onready var label_pos: Label = $PanelContainer/VBoxContainer/Position
@onready var label_chunk: Label = $PanelContainer/VBoxContainer/Chunk
@onready var label_terrain: Label = $PanelContainer/VBoxContainer/Terrain
@onready var label_id: Label = $PanelContainer/VBoxContainer/TileID
@onready var close_button: Button = $PanelContainer/VBoxContainer/CloseButton

func _ready() -> void:
	panel.hide()
	close_button.pressed.connect(_on_close_button_pressed)

## Populates inspector fields for coordinates mapping.
func display_tile_info(tile_data: Dictionary, chunk_size: int) -> void:
	var x = tile_data["x"]
	var y = tile_data["y"]

	# Math-safe division flooring
	var cx: int = floori(float(x) / chunk_size)
	var cy: int = floori(float(y) / chunk_size)

	label_pos.text = "World Position: (%d, %d)" % [x, y]
	label_chunk.text = "Chunk Position: (%d, %d)" % [cx, cy]
	label_terrain.text = "Terrain: %s" % str(tile_data["terrain"]).capitalize()
	label_id.text = "Tile ID: %s" % (tile_data["id"] if tile_data["id"] != "" else "N/A")

	panel.show()

func _on_close_button_pressed() -> void:
	panel.hide()
