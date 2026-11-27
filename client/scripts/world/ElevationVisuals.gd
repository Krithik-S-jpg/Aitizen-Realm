extends RefCounted
const STEP := 36.0

static func level(tiles: Dictionary, at: Vector2i) -> int:
	var meta: Dictionary = tiles.get(at,{}).get("metadata",{})
	return clampi(int(meta.get("bridge_level",meta.get("terrace",0))),0,4)

static func ground_level(tiles: Dictionary, at: Vector2i) -> int:
	return clampi(int(tiles.get(at,{}).get("metadata",{}).get("terrace",0)),0,4)

static func faces(renderer, at: Vector2i, center: Vector2) -> void:
	var height := ground_level(renderer._tiles,at)
	var diamond: PackedVector2Array = renderer._diamond_at(center)
	for edge: int in range(2):
		var delta := Vector2i(1,0) if edge == 0 else Vector2i(0,1)
		var drop := height-ground_level(renderer._tiles,at+delta)
		if drop <= 0:
			continue
		var a := diamond[1+edge]
		var b := diamond[2+edge]
		var down := Vector2(0,drop*STEP)
		var face := PackedVector2Array([a,b,b+down,a+down])
		var tint := Color("e0daca") if edge == 0 else Color("abae9e")
		var u := float(at.x if edge == 0 else at.y)*.25
		renderer.draw_polygon(face,PackedColorArray([tint]),PackedVector2Array([Vector2(u,0),Vector2(u+.25,0),Vector2(u+.25,drop*.2),Vector2(u,drop*.2)]),renderer._ground_material("cliff-face"))
		var tile: Dictionary = renderer._tiles[at]
		var neighbor: Dictionary = renderer._tiles.get(at+delta,{})
		var waterfall := str(tile.get("terrain","")).to_lower() in ["water","ocean"] and str(neighbor.get("terrain","")).to_lower() in ["water","ocean"]
		var ramps: Array = tile.get("metadata",{}).get("ramps",[])
		if waterfall:
			renderer.draw_colored_polygon(face,Color(.21,.60,.69,.83))
			for stream: int in range(6):
				var p := a.lerp(b,(stream+.5)/6.0)
				var phase := fposmod(float(renderer._visual_seconds)*.8+stream*.17,1)
				renderer.draw_line(p+down*phase,p+down*minf(1,phase+.32),Color(.73,.89,.85,.6),2)
			renderer.draw_line(a+down,b+down,Color(.8,.9,.85,.7),3)
			if renderer._quality_detail_cap > 0:
				for foam: int in range(5):
					var spread := fposmod(float(renderer._visual_seconds)*.35+foam*.21,1.0)
					var landing := (a+down).lerp(b+down,(foam+.5)/5.0)+Vector2(0,spread*7)
					renderer.draw_arc(landing,2+spread*5,0,PI,7,Color(.79,.89,.84,(1-spread)*.38),1)
		else:
			# Broken sod edge and shaded stone facets soften the perfect tile seam.
			var seed := posmod(at.x*73+at.y*37+edge*19,101)
			renderer.draw_line(a+down,b+down,Color(.12,.16,.12,.25),4)
			for section: int in range(5):
				var t := float(section)/5.0
				var left := a.lerp(b,t)
				var right := a.lerp(b,t+.2)
				var depth := 2.0+float((seed+section*7)%6)
				renderer.draw_colored_polygon(PackedVector2Array([left,right,right+Vector2(-1,depth*.65),left+Vector2(1,depth)]),Color("78805c"))
				if renderer._quality_detail_cap > 0:
					var rock := left+down*(.3+float((seed+section)%4)*.12)
					renderer.draw_colored_polygon(PackedVector2Array([rock,rock+Vector2(7,-3),rock+Vector2(10,4),rock+Vector2(2,7)]),Color(.59,.57,.47,.28))
					if (seed+section)%3 == 0:
						renderer.draw_line(left+Vector2(2,3),left+Vector2(1,minf(drop*STEP*.65,12)),Color(.32,.39,.22,.65),2)
			if renderer._quality_detail_cap > 0 and not str(neighbor.get("terrain","")).to_lower() in ["water","ocean"]:
				for stone: int in range(3):
					var foot := (a+down).lerp(b+down,(stone+.4)/3.0)
					var size := 2.0+float((seed+stone)%4)
					renderer.draw_colored_polygon(PackedVector2Array([foot+Vector2(-size,0),foot+Vector2(-size*.4,-size),foot+Vector2(size*.6,-size*.7),foot+Vector2(size,1),foot+Vector2(0,3)]),Color("85816c"))
		if [at.x+delta.x,at.y+delta.y] in ramps:
			for step: int in range(6):
				var p := a.lerp(b,.5)+Vector2(0,(step+.5)*STEP/6)
				renderer.draw_line(p-Vector2(7,0),p+Vector2(7,0),Color("b5a98a"),3)
