extends "res://scripts/world/WorldRenderer.gd"

var elapsed := 0.0
const ACTIONS := ["idle", "move", "carry", "build", "sleep", "gather"]

func _ready() -> void:
	pass

func _process(delta: float) -> void:
	elapsed += delta
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(0,0,1200,650),Color("243b34"))
	for column: int in range(ACTIONS.size()):
		draw_string(ThemeDB.fallback_font,Vector2(65+column*190,45),ACTIONS[column],HORIZONTAL_ALIGNMENT_LEFT,-1,18)
	for row: int in range(2):
		for column: int in range(ACTIONS.size()):
			var anchor := Vector2(100+column*190,280+row*280)
			draw_line(anchor-Vector2(70,0),anchor+Vector2(70,0),Color("7d8b72"))
			draw_set_transform(anchor,0,Vector2(3,3))
			_draw_agent_sprite(Vector2.ZERO,ACTIONS[column],elapsed,"adult_male" if row==0 else "adult_female")
			draw_set_transform(Vector2.ZERO)
