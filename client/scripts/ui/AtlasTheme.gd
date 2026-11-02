extends RefCounted

static var reduced_motion := false


static func reveal(control: Control) -> void:
	var previous: Variant = control.get_meta("atlas_reveal") if control.has_meta("atlas_reveal") else null
	if previous is Tween and previous.is_valid():
		previous.kill()
	control.self_modulate.a = 1.0
	control.modulate.a = 1.0
	if reduced_motion or not control.is_visible_in_tree():
		return
	control.modulate.a = 0.0
	var tween := control.create_tween()
	control.set_meta("atlas_reveal", tween)
	tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.tween_property(control, "modulate:a", 1.0, 0.22)


static func surface(color: String, radius: int = 10) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(color)
	style.set_corner_radius_all(radius)
	return style


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
static func apply_to(node: Node, recursive: bool = true) -> void:
	if node is Control:
		node.add_theme_color_override("font_color", Color("e4edf4"))
	if node is PanelContainer or node is Panel:
		if not node.has_meta("atlas_reveal_bound"):
			node.set_meta("atlas_reveal_bound", true)
			node.visibility_changed.connect(func() -> void: reveal(node))
	if node is PopupPanel or node is AcceptDialog:
		var modal := surface("101d2e", 14)
		modal.border_color = Color("3d6277")
		modal.set_border_width_all(1)
		modal.set_content_margin_all(16)
		node.add_theme_stylebox_override("panel", modal)
	if node is ProgressBar:
		node.add_theme_stylebox_override("background", surface("1a2c40", 7))
		node.add_theme_stylebox_override("fill", surface("64cfba", 7))
	if node is VScrollBar or node is HScrollBar:
		node.add_theme_stylebox_override("scroll", surface("0d1725", 4))
		for state: String in ["grabber", "grabber_highlight", "grabber_pressed"]:
			var grip := surface("4c7185" if state == "grabber" else "76d3c0", 4)
			grip.set_content_margin_all(4)
			node.add_theme_stylebox_override(state, grip)
	if node is PanelContainer or node is Panel:
		var panel := StyleBoxFlat.new()
		panel.bg_color = Color("0d1929f5")
		panel.border_color = Color("30485f")
		panel.set_border_width_all(1)
		panel.border_width_left = 2
		panel.set_corner_radius_all(12)
		panel.shadow_color = Color("020b1266")
		panel.shadow_size = 14
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
			button_style.bg_color = Color("172b3c")
			button_style.border_color = Color("365268")
			if state in ["hover", "focus"]:
				button_style.bg_color = Color("204139")
				button_style.border_color = Color("76d3c0")
			elif state == "pressed":
				button_style.bg_color = Color("235143")
				button_style.border_color = Color("9ae8cd")
			elif state == "disabled":
				button_style.bg_color = Color("17242c")
			button_style.set_border_width_all(1)
			button_style.set_corner_radius_all(8)
			var previous: StyleBox = node.get_theme_stylebox(state)
			for side: int in range(4):
				button_style.set_content_margin(side, previous.get_content_margin(side))
			node.add_theme_stylebox_override(state, button_style)
		node.add_theme_color_override("font_color", Color("dfedea"))
		node.add_theme_color_override("font_hover_color", Color("ffffff"))
		node.add_theme_color_override("font_disabled_color", Color("718793"))
	if node is LineEdit:
		var field := StyleBoxFlat.new()
		field.bg_color = Color("091320")
		field.border_color = Color("365268")
		field.set_border_width_all(1)
		field.set_corner_radius_all(8)
		field.content_margin_left = 10
		field.content_margin_top = 7
		field.content_margin_bottom = 7
		node.add_theme_stylebox_override("normal", field)
		var focused := field.duplicate() as StyleBoxFlat
		focused.border_color = Color("76d3c0")
		node.add_theme_stylebox_override("focus", focused)
		node.add_theme_color_override("font_color", Color("e2e9dd"))
	if node is Tree:
		var surface := StyleBoxFlat.new()
		surface.bg_color = Color("0c1725")
		surface.border_color = Color("30485f")
		surface.set_corner_radius_all(8)
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
	if recursive:
		for child: Node in node.get_children():
			apply_to(child)
