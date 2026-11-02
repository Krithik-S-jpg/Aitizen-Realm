extends RefCounted

static func paint(canvas: CanvasItem, kind: String) -> void:
	canvas.draw_colored_polygon(PackedVector2Array([Vector2(-35, 0), Vector2(0, -17), Vector2(38, 0), Vector2(0, 16)]), Color("525e50"))
	var count := 3 if kind == "abandoned_settlement" else 1
	for index in range(count):
		var x := (index - 1) * 24 if count == 3 else -12
		var height := 65 if kind == "ruined_tower" else 38
		canvas.draw_colored_polygon(PackedVector2Array([Vector2(x, 0), Vector2(x, -height), Vector2(x+10, -height-7), Vector2(x+22, -height+3), Vector2(x+22, -6)]), Color("8a9282"))
		canvas.draw_colored_polygon(PackedVector2Array([Vector2(x+22, -6), Vector2(x+22, -height+3), Vector2(x+30, -height+9), Vector2(x+30, 0)]), Color("56685e"))
		for row in range(2, height, 12):
			canvas.draw_line(Vector2(x, -row), Vector2(x+21, -row+2), Color("4c5b52"), 1)
		canvas.draw_polyline(PackedVector2Array([Vector2(x+9, -31), Vector2(x+15, -24), Vector2(x+8, -18), Vector2(x+15, -12)]), Color("dcc58a"), 2)
		canvas.draw_circle(Vector2(x+21, -3), 5, Color("5a7d50"))
