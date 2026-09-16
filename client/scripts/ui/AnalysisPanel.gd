extends Control
class_name AnalysisPanel

## Modal research/history surface; the live world remains visible beneath it.

signal refresh_requested()

var _panel: PanelContainer
var _title: Label
var _subtitle: Label
var _content: RichTextLabel
var _mode := "research"
var _tween: Tween


func _ready() -> void:
	_build()
	hide()


func open_mode(mode: String) -> void:
	_mode = mode
	_title.text = "RESEARCH LAB" if mode == "research" else "WORLD HISTORY"
	_subtitle.text = "Experiments · runs · metrics · exports" if mode == "research" else "Backend-recorded events in chronological context"
	_content.text = "[color=#72d6bb]Synchronizing authoritative simulation data…[/color]"
	show()
	_panel.modulate.a = 0.0
	_panel.scale = Vector2(0.97, 0.97)
	_panel.pivot_offset = _panel.size * 0.5
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	_tween.tween_property(_panel, "modulate:a", 1.0, 0.2)
	_tween.tween_property(_panel, "scale", Vector2.ONE, 0.26)
	refresh_requested.emit()


func close_panel() -> void:
	if not visible:
		return
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	_tween.tween_property(_panel, "modulate:a", 0.0, 0.15)
	_tween.tween_property(_panel, "scale", Vector2(0.98, 0.98), 0.15)
	_tween.chain().tween_callback(hide)


func display_observation(data: Dictionary) -> void:
	_content.text = _research_text(data) if _mode == "research" else _history_text(data)


func display_error(message: String) -> void:
	_content.text = "[color=#e98a7b]UNAVAILABLE[/color]\n\n%s" % message


func _research_text(data: Dictionary) -> String:
	var metrics: Array = data.get("metrics", [])
	var experiments: Array = data.get("experiments", [])
	var world: Dictionary = data.get("world", {})
	var lines: Array[String] = [
		"[color=#72d6bb][b]CURRENT RESEARCH STATE[/b][/color]",
		"World seed: %s   Bounds: %s × %s   Chunks: %s" % [world.get("seed", "N/A"), world.get("width", "N/A"), world.get("height", "N/A"), world.get("chunks", "N/A")],
		"",
		"[b]METRICS[/b]"
	]
	if metrics.is_empty():
		lines.append("No completed tick measurements yet. Start or step the simulation.")
	else:
		var latest: Dictionary = metrics[-1]
		lines.append("Tick %d   Population %d   Groups %d   Structures %d" % [int(latest.get("tick", 0)), int(latest.get("population", 0)), int(latest.get("groups", 0)), int(latest.get("structures", 0))])
		lines.append("Average health %.1f   Average hunger %.1f   Resources %.1f" % [float(latest.get("average_health", 0.0)), float(latest.get("average_hunger", 0.0)), float(latest.get("resources_available", 0.0))])
	lines.append("\n[b]EXPERIMENTS  %d[/b]" % experiments.size())
	for experiment: Dictionary in experiments.slice(maxi(0, experiments.size() - 8)):
		lines.append("• %s   %s   seed %s" % [experiment.get("name", "Unnamed"), experiment.get("status", "DRAFT"), experiment.get("seed", "N/A")])
	return "\n".join(lines)


func _history_text(data: Dictionary) -> String:
	var timeline: Array = data.get("timeline", [])
	var lines: Array[String] = ["[color=#e5c574][b]RECORDED TIMELINE[/b][/color]"]
	if timeline.is_empty():
		lines.append("\nNo historical episodes have been recorded yet.")
		return "\n".join(lines)
	for index in range(maxi(0, timeline.size() - 30), timeline.size()):
		var event: Dictionary = timeline[index]
		lines.append("[color=#72d6bb]T%05d[/color]  %s  —  %s" % [int(event.get("tick", 0)), str(event.get("type", "event")).to_upper(), event.get("summary", "")])
	return "\n".join(lines)


func _build() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.offset_left = 250.0
	_panel.offset_top = 126.0
	_panel.offset_right = -250.0
	_panel.offset_bottom = -118.0
	var style := StyleBoxFlat.new()
	style.bg_color = Color("07151ded")
	style.border_color = Color("347080")
	style.set_border_width_all(1)
	style.set_corner_radius_all(14)
	style.shadow_color = Color(0, 0, 0, 0.5)
	style.shadow_size = 12
	_panel.add_theme_stylebox_override("panel", style)
	add_child(_panel)
	var margin := MarginContainer.new()
	for side in ["margin_left", "margin_top", "margin_right", "margin_bottom"]:
		margin.add_theme_constant_override(side, 22)
	_panel.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	margin.add_child(column)
	var header := HBoxContainer.new()
	column.add_child(header)
	var titles := VBoxContainer.new()
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(titles)
	_title = Label.new()
	_title.add_theme_font_size_override("font_size", 23)
	_title.add_theme_color_override("font_color", Color("e8e0cf"))
	titles.add_child(_title)
	_subtitle = Label.new()
	_subtitle.add_theme_color_override("font_color", Color("91a8af"))
	titles.add_child(_subtitle)
	var refresh := Button.new()
	refresh.text = "↻  REFRESH"
	refresh.pressed.connect(func() -> void: refresh_requested.emit())
	header.add_child(refresh)
	var close := Button.new()
	close.text = "×  CLOSE"
	close.pressed.connect(close_panel)
	header.add_child(close)
	_content = RichTextLabel.new()
	_content.bbcode_enabled = true
	_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_content.add_theme_font_size_override("normal_font_size", 14)
	_content.add_theme_constant_override("line_separation", 6)
	column.add_child(_content)
