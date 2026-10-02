extends Control
class_name WorldEventOverlay

## Compact animated notifications generated from real backend state changes.

signal navigate_requested(map_position: Vector2i)

var _stack: VBoxContainer
var _seen: Dictionary = {}

const EVENT_COLORS := {
	"info": Color("6ea9c5"),
	"success": Color("65d6a6"),
	"warning": Color("e2bd69"),
	"danger": Color("e77b69")
}
const EVENT_ICONS := {
	"birth": "✦",
	"death": "◆",
	"hunt": "⚠",
	"construction": "⌂",
	"tree_felled": "♣",
	"crafted": "⚒",
	"harvest": "❧",
	"society": "♟",
	"weather": "☂",
	"sleep": "☾",
	"wake": "☀"
}


func _ready() -> void:
	set_anchors_preset(Control.PRESET_TOP_RIGHT)
	position = Vector2(-354, 158)
	size = Vector2(336, 430)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stack = VBoxContainer.new()
	_stack.set_anchors_preset(Control.PRESET_TOP_WIDE)
	_stack.add_theme_constant_override("separation", 8)
	add_child(_stack)


func display_events(events: Array) -> void:
	for event_value: Variant in events:
		if event_value is Dictionary:
			_add_event(event_value as Dictionary)


func _add_event(event: Dictionary) -> void:
	var event_id := str(event.get("id", "%s:%s" % [event.get("tick", 0), event.get("title", "event")]))
	if _seen.has(event_id):
		return
	_seen[event_id] = true
	if _seen.size() > 2000:
		_seen.erase(_seen.keys()[0])
	var severity := str(event.get("severity", "info")).to_lower()
	var accent: Color = EVENT_COLORS.get(severity, EVENT_COLORS["info"])
	var card := Button.new()
	card.custom_minimum_size = Vector2(336, 72)
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	card.focus_mode = Control.FOCUS_NONE
	card.alignment = HORIZONTAL_ALIGNMENT_LEFT
	card.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.text = "%s   %s\n      %s   ·   T%05d" % [
		EVENT_ICONS.get(str(event.get("event_type", "")), "•"),
		str(event.get("title", "World event")).to_upper(),
		str(event.get("summary", "")),
		int(event.get("tick", 0))
	]
	card.add_theme_font_size_override("font_size", 11)
	card.add_theme_color_override("font_color", Color("dbe8e6"))
	card.add_theme_color_override("font_hover_color", Color.WHITE)
	card.add_theme_stylebox_override("normal", _style(Color("07171def"), accent.darkened(0.25)))
	card.add_theme_stylebox_override("hover", _style(Color("10262cef"), accent))
	card.tooltip_text = "Click to focus this event" if event.get("x") != null and event.get("y") != null else "Recorded world event"
	if event.get("x") != null and event.get("y") != null:
		var coordinate := Vector2i(int(event["x"]), int(event["y"]))
		card.pressed.connect(func() -> void: navigate_requested.emit(coordinate))
	_stack.add_child(card)
	_stack.move_child(card, 0)
	while _stack.get_child_count() > 5:
		var oldest := _stack.get_child(_stack.get_child_count() - 1)
		_stack.remove_child(oldest)
		oldest.queue_free()
	card.modulate.a = 0.0
	card.position.x = 48.0
	var tween := card.create_tween().set_parallel(true).set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	tween.tween_property(card, "modulate:a", 1.0, 0.2)
	tween.tween_property(card, "position:x", 0.0, 0.3)
	var expiry := card.create_tween()
	expiry.tween_interval(8.0 if severity in ["warning", "danger"] else 6.0)
	expiry.tween_property(card, "modulate:a", 0.0, 0.35)
	expiry.tween_callback(card.queue_free)


func _style(background: Color, accent: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = accent
	style.border_width_left = 3
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.set_corner_radius_all(9)
	style.content_margin_left = 12
	style.content_margin_right = 10
	style.content_margin_top = 9
	style.content_margin_bottom = 9
	style.shadow_color = Color(0, 0, 0, 0.4)
	style.shadow_size = 7
	return style
