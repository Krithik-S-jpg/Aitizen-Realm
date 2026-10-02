extends RefCounted

static var reduced_motion := false


static func animate_button(control: Control, highlighted: bool) -> void:
	var previous: Variant = control.get_meta("atlas_hover_tween") if control.has_meta("atlas_hover_tween") else null
	if previous is Tween and previous.is_valid():
		previous.kill()
	var tint := Color("bdebe1") if highlighted else Color.WHITE
	if reduced_motion:
		control.modulate = tint
		return
	var tween := control.create_tween()
	control.set_meta("atlas_hover_tween", tween)
	tween.tween_property(control, "modulate", tint, 0.14)

## One visual language for all observatory panels, including modal tools.
static func apply_to(node: Node) -> void:
	if node is PanelContainer or node is Panel:
		var panel := StyleBoxFlat.new()
		panel.bg_color = Color("091716")
		panel.border_color = Color("35524d")
		panel.set_border_width_all(1)
		panel.border_width_left = 2
		panel.set_corner_radius_all(5)
		panel.shadow_color = Color("020b1266")
		panel.shadow_size = 8
		var previous: StyleBox = node.get_theme_stylebox("panel")
		for side: int in range(4):
			panel.set_content_margin(side, previous.get_content_margin(side))
		node.add_theme_stylebox_override("panel", panel)
	if node is Button and not node is CheckBox and not node is CheckButton:
		if not node.has_meta("atlas_hover_bound"):
			node.set_meta("atlas_hover_bound", true)
			node.mouse_entered.connect(func() -> void: animate_button(node, true))
			node.mouse_exited.connect(func() -> void: animate_button(node, false))
			node.focus_entered.connect(func() -> void: animate_button(node, true))
			node.focus_exited.connect(func() -> void: animate_button(node, false))
		for state: String in ["normal", "hover", "pressed", "disabled", "focus"]:
			var button_style := StyleBoxFlat.new()
			button_style.bg_color = Color("102522")
			button_style.border_color = Color("35524d")
			if state in ["hover", "focus"]:
				button_style.bg_color = Color("204139")
				button_style.border_color = Color("76d3c0")
			elif state == "pressed":
				button_style.bg_color = Color("235143")
				button_style.border_color = Color("9ae8cd")
			elif state == "disabled":
				button_style.bg_color = Color("17242c")
			button_style.set_border_width_all(1)
			button_style.set_corner_radius_all(4)
			var previous: StyleBox = node.get_theme_stylebox(state)
			for side: int in range(4):
				button_style.set_content_margin(side, previous.get_content_margin(side))
			node.add_theme_stylebox_override(state, button_style)
		node.add_theme_color_override("font_color", Color("dfedea"))
		node.add_theme_color_override("font_hover_color", Color("ffffff"))
		node.add_theme_color_override("font_disabled_color", Color("718793"))
	if node is LineEdit:
		var field := StyleBoxFlat.new()
		field.bg_color = Color("071311")
		field.border_color = Color("35524d")
		field.set_border_width_all(1)
		field.set_corner_radius_all(4)
		field.content_margin_left = 10
		field.content_margin_top = 7
		field.content_margin_bottom = 7
		node.add_theme_stylebox_override("normal", field)
		node.add_theme_color_override("font_color", Color("e2e9dd"))
	if node is Tree:
		var surface := StyleBoxFlat.new()
		surface.bg_color = Color("0a1916")
		surface.border_color = Color("304d44")
		surface.set_border_width_all(1)
		node.add_theme_stylebox_override("panel", surface)
		var selected := StyleBoxFlat.new()
		selected.bg_color = Color("234d3f")
		selected.border_color = Color("80c9af")
		selected.border_width_left = 2
		node.add_theme_stylebox_override("selected", selected)
		node.add_theme_stylebox_override("selected_focus", selected)
		node.add_theme_color_override("font_color", Color("dfe7dc"))
		node.add_theme_font_size_override("font_size", 13)
		node.add_theme_constant_override("v_separation", 12)
		node.add_theme_constant_override("h_separation", 10)
	for child: Node in node.get_children():
		apply_to(child)
