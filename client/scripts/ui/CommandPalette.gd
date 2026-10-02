extends PopupPanel

signal navigate_requested(mode: String)

var _search: LineEdit
var _results: VBoxContainer
const DESTINATIONS := {"world": "World overview", "citizens": "Citizens / inspect and manage", "animals": "Animals / wildlife and habitats", "buildings": "Buildings / work and supplies", "settlements": "Settlements / social groups", "economy": "Economy / material stock", "build": "Build / known recipes", "research": "Research / experiments", "history": "History / event timeline", "settings": "Settings / clock and weather"}


func _ready() -> void:
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 8)
	add_child(layout)
	_search = LineEdit.new()
	_search.placeholder_text = "Search pages and tools…"
	layout.add_child(_search)
	_results = VBoxContainer.new()
	layout.add_child(_results)
	_search.text_changed.connect(func(_text: String) -> void: _refresh())
	_search.text_submitted.connect(func(_text: String) -> void:
		if _results.get_child_count() > 0:
			_results.get_child(0).pressed.emit()
	)
	_refresh()


func open_search() -> void:
	_search.clear()
	_refresh()
	popup_centered(Vector2i(470, 380))
	_search.grab_focus()


func _refresh() -> void:
	for child: Node in _results.get_children():
		_results.remove_child(child)
		child.queue_free()
	for mode: String in DESTINATIONS:
		if not str(DESTINATIONS[mode]).to_lower().contains(_search.text.to_lower()):
			continue
		var button := Button.new()
		button.text = DESTINATIONS[mode]
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.custom_minimum_size.y = 34
		button.pressed.connect(func() -> void:
			hide()
			navigate_requested.emit(mode)
		)
		_results.add_child(button)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(_results)
