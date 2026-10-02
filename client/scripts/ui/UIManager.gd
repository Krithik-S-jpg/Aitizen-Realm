extends Node
class_name UIManager

## Coordinates mutually exclusive UI modes and immersive world focus.

@onready var hud: DebugHUD = get_node("../DebugPanel") as DebugHUD
@onready var crafting: CraftingPanel = get_node("../CraftingPanel") as CraftingPanel
@onready var admin: AdminPanel = get_node("../AdminPanel") as AdminPanel
@onready var inspector: TileInspector = get_node("../TileInspector") as TileInspector
@onready var minimap: WorldMinimap = get_node("../WorldMinimap") as WorldMinimap
@onready var analysis: AnalysisPanel = get_node("../AnalysisPanel") as AnalysisPanel

var current_mode := "world"
var left_panel_pinned := false
var right_panel_pinned := false
var _overview_visible := false
var _palette: PopupPanel


func _ready() -> void:
	_palette = preload("res://scripts/ui/CommandPalette.gd").new()
	add_child(_palette)
	_palette.navigate_requested.connect(func(mode: String) -> void: hud.navigation_requested.emit(mode))
	minimap.hide()
	hud.call_deferred("attach_minimap", minimap)
	hud.navigation_requested.connect(_navigate)
	analysis.navigation_requested.connect(func(mode: String) -> void: hud.navigation_requested.emit(mode))
	hud.focus_mode_requested.connect(_set_focus_mode)
	hud.overview_visibility_changed.connect(_set_overview_visible)
	call_deferred("_apply_atlas_theme")


func _apply_atlas_theme() -> void:
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(get_parent())


func _navigate(mode: String) -> void:
	if mode == "search":
		_palette.open_search()
		return
	current_mode = mode
	hud.select_navigation(mode)
	var events := get_node_or_null("../WorldEventOverlay") as Control
	if events != null:
		events.visible = mode in ["world", "build"]
	if mode != "world":
		inspector.hide_inspector()
	if mode != "build":
		crafting.close_panel()
	if mode != "citizens":
		admin.close_page()
	if mode not in ["animals", "buildings", "research", "history", "settlements", "economy"]:
		analysis.close_panel()
	match mode:
		"world":
			pass
		"citizens":
			hud.admin_requested.emit()
		"build":
			hud.crafting_requested.emit()
		"animals", "buildings", "research", "history", "settlements", "economy":
			analysis.open_mode(mode)


func _set_focus_mode(enabled: bool) -> void:
	if enabled:
		crafting.close_panel()
		admin.close_page()
		analysis.close_panel()
		inspector.hide_inspector()
	minimap.visible = not enabled and _overview_visible


func _set_overview_visible(is_visible: bool) -> void:
	_overview_visible = is_visible
	minimap.visible = is_visible


func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.keycode == KEY_K:
		_palette.open_search()
		get_viewport().set_input_as_handled()
