# HUD.gd
extends Control
class_name HUD

## Displays client status metrics, including connection state and loaded world attributes.

signal reload_requested()

@onready var label_status: Label = $MarginContainer/VBoxContainer/ConnectionStatus
@onready var label_url: Label = $MarginContainer/VBoxContainer/BackendURL
@onready var label_size: Label = $MarginContainer/VBoxContainer/WorldSize
@onready var label_chunk: Label = $MarginContainer/VBoxContainer/ChunkSize
@onready var label_tiles: Label = $MarginContainer/VBoxContainer/LoadedTileCount
@onready var label_fps: Label = $MarginContainer/VBoxContainer/FPS
@onready var label_tps: Label = $MarginContainer/VBoxContainer/TPS
@onready var retry_button: Button = $MarginContainer/VBoxContainer/RetryButton

func _ready() -> void:
	retry_button.pressed.connect(_on_retry_pressed)
	retry_button.hide()

## Formats HUD state to show connection success.
func update_status(is_connected: bool, error_msg: String = "") -> void:
	if is_connected:
		label_status.text = "Connection Status: Connected"
		label_status.add_theme_color_override("font_color", Color.GREEN)
		retry_button.hide()
	else:
		label_status.text = "Connection Status: Disconnected (%s)" % (error_msg if error_msg != "" else "Unavailable")
		label_status.add_theme_color_override("font_color", Color.RED)
		retry_button.show()

## Formats HUD metrics to match active map state.
func update_world_info(url: String, width: int, height: int, chunk_size: int, tiles_count: int) -> void:
	label_url.text = "Backend URL: %s" % url
	label_size.text = "World Size: %d x %d" % [width, height]
	label_chunk.text = "Chunk Size: %d" % chunk_size
	label_tiles.text = "Loaded Tile Count: %d" % tiles_count
	label_tps.text = "TPS (Sim Rate): Placeholder (Pending Clock integration)"

func _process(_delta: float) -> void:
	label_fps.text = "FPS: %d" % Engine.get_frames_per_second()

func _on_retry_pressed() -> void:
	emit_signal("reload_requested")
