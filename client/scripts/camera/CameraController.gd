# CameraController.gd
extends Camera2D
class_name CameraController

## Manages viewport navigation, supporting middle-mouse dragging, scrolling zoom, and smooth lerping.

@export var drag_speed: float = 1.0
@export var min_zoom: float = 0.2
@export var max_zoom: float = 4.0
@export var zoom_speed: float = 0.15
@export var smooth_speed: float = 12.0
@export var keyboard_pan_speed: float = 520.0

# Viewport bounds
@export var limit_left_val: int = -10000
@export var limit_top_val: int = -10000
@export var limit_right_val: int = 10000
@export var limit_bottom_val: int = 10000

var _target_zoom: float = 1.0
var _is_dragging: bool = false
var _follow_target := Vector2.ZERO
var _has_follow_target := false

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
		_has_follow_target = false
		position -= event.relative * (1.0 / zoom.x) * drag_speed

func _process(delta: float) -> void:
	var direction := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if direction != Vector2.ZERO:
		_has_follow_target = false
		position += direction * keyboard_pan_speed * delta / zoom.x

	# Exponential interpolation cannot overshoot during a slow frame. The previous
	# raw lerp weight could exceed 1.0 and made the entire view pulse when zooming.
	var zoom_weight := 1.0 - exp(-smooth_speed * delta)
	var stable_zoom := lerpf(zoom.x, _target_zoom, zoom_weight)
	zoom = Vector2(stable_zoom, stable_zoom)
	if _has_follow_target:
		var follow_weight := 1.0 - exp(-7.0 * delta)
		position = position.lerp(_follow_target, follow_weight)


func set_follow_target(world_position: Vector2) -> void:
	_follow_target = world_position
	_has_follow_target = true


func clear_follow_target() -> void:
	_has_follow_target = false


func jump_to(world_position: Vector2) -> void:
	position = world_position
	_follow_target = world_position
