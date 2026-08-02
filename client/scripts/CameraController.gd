# CameraController.gd
extends Camera2D
class_name CameraController

## Implements smooth panning, zooming, and limits for the isometric world camera.

@export var drag_speed: float = 1.0
@export var min_zoom: float = 0.2
@export var max_zoom: float = 4.0
@export var zoom_speed: float = 0.15
@export var smooth_speed: float = 15.0

var _target_zoom: float = 1.0
var _is_dragging: bool = false

func _ready() -> void:
	_target_zoom = zoom.x

func _unhandled_input(event: InputEvent) -> void:
	# Panning via Right Mouse Button drag
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
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
	# Smooth lerp zoom
	zoom.x = lerp(zoom.x, _target_zoom, smooth_speed * delta)
	zoom.y = lerp(zoom.y, _target_zoom, smooth_speed * delta)
