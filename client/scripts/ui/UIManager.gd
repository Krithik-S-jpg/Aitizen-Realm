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


func _ready() -> void:
	minimap.hide()
	hud.call_deferred("attach_minimap", minimap)
	hud.navigation_requested.connect(_navigate)
	hud.focus_mode_requested.connect(_set_focus_mode)
	hud.overview_visibility_changed.connect(_set_overview_visible)


func _navigate(mode: String) -> void:
	current_mode = mode
	if mode != "build":
		crafting.close_panel()
	if mode != "citizens":
		admin.close_page()
	if mode not in ["research", "history"]:
		analysis.close_panel()
	match mode:
		"world":
			pass
		"citizens":
			hud.admin_requested.emit()
		"build":
			hud.crafting_requested.emit()
		"research", "history":
			analysis.open_mode(mode)
		"settings":
			hud.toggle_settings()


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
