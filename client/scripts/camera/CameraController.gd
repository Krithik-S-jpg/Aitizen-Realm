# CameraController.gd
extends Camera2D
class_name CameraController

## Manages viewport navigation, supporting middle-mouse dragging, scrolling zoom, and smooth lerping.

@export var drag_speed: float = 1.0
@export var min_zoom: float = 0.2
@export var max_zoom: float = 4.0
@export var zoom_speed: float = 0.15
@export var smooth_speed: float = 12.0

# Viewport bounds
@export var limit_left_val: int = -10000
@export var limit_top_val: int = -10000
@export var limit_right_val: int = 10000
@export var limit_bottom_val: int = 10000

var _target_zoom: float = 1.0
var _is_dragging: bool = false

func _ready() -> void:
	_target_zoom = zoom.x
	limit_left = limit_left_val
	limit_top = limit_top_val
	limit_right = limit_right_val
	limit_bottom = limit_bottom_val

func _unhandled_input(event: InputEvent) -> void:
	# Panning via middle mouse drag
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_MIDDLE:
			if event.pressed:
				_is_dragging = true
			else:
				_is_dragging = false

		# Zooming via mouse wheel
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_target_zoom = clamp(_target_zoom + zoom_speed, min_zoom, max_zoom)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_target_zoom = clamp(_target_zoom - zoom_speed, min_zoom, max_zoom)

	elif event is InputEventMouseMotion and _is_dragging:
		position -= event.relative * (1.0 / zoom.x) * drag_speed

func _process(delta: float) -> void:
	# Smooth lerping
	zoom.x = lerp(zoom.x, _target_zoom, smooth_speed * delta)
	zoom.y = lerp(zoom.y, _target_zoom, smooth_speed * delta)
