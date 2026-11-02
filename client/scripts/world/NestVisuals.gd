extends RefCounted

static func paint(canvas: CanvasItem, center: Vector2, eggs: int, progress: float = 1.0) -> void:
	canvas.draw_set_transform(center, 0, Vector2(1, .58))
	canvas.draw_circle(Vector2(1, 3), 12, Color(0, 0, 0, .18))
	canvas.draw_circle(Vector2.ZERO, 11, Color("59402c"))
	canvas.draw_circle(Vector2(0, -1), 7, Color("302d25"))
	for twig in range(maxi(4, int(32 * progress))):
		var angle := twig * 2.39996
		var radius := 8.5 + sin(twig * 7.1) * 2
		var point := Vector2.from_angle(angle) * radius
		var tangent := Vector2.from_angle(angle + PI / 2) * (3 + twig % 3)
		canvas.draw_line(point - tangent, point + tangent, [Color("a88650"), Color("725237"), Color("c2a272")][twig % 3], 1.3, true)
	canvas.draw_set_transform(Vector2.ZERO)
	for index in range(mini(eggs, 3)):
		var egg := center + Vector2((index - (minf(eggs, 3) - 1) * .5) * 4.5, -1)
		canvas.draw_set_transform(egg, -.25 + index * .3, Vector2(.8, 1))
		canvas.draw_circle(Vector2.ZERO, 3, Color("e0dec5"))
		canvas.draw_circle(Vector2(-.7, -.8), 1.5, Color("f4f0d7"))
		canvas.draw_circle(Vector2(.8, .5), .6, Color("8a8167"))
		canvas.draw_set_transform(Vector2.ZERO)
