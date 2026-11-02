extends "res://scripts/world/WorldRenderer.gd"

var sample_time := 0.0
const PEOPLE := ["scout", "builder", "herbalist", "scholar", "cook", "miner", "fisher", "artisan", "juniper", "rowan", "family_infant", "family_toddler_male", "family_toddler_female", "family_child_male", "family_child_female", "family_teen_male", "family_teen_female", "family_elder_male", "family_elder_female"]
const POSES := ["idle", "move", "sleep", "gather", "build", "swim", "cook", "hunt"]

func _ready() -> void:
	pass

func _process(_delta: float) -> void:
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(0, 0, 1500, 1500), Color("17252b"))
	for column in range(POSES.size()):
		draw_string(ThemeDB.fallback_font, Vector2(230 + column * 150, 24), POSES[column], HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
	for row in range(PEOPLE.size()):
		var avatar: String = PEOPLE[row]
		draw_string(ThemeDB.fallback_font, Vector2(10, 83 + row * 73), avatar, HORIZONTAL_ALIGNMENT_LEFT, -1, 14)
		for column in range(POSES.size()):
			if avatar.begins_with("family_") and column > 2:
				continue
			_draw_agent_sprite(Vector2(260 + column * 150, 95 + row * 73), POSES[column], sample_time, avatar)
