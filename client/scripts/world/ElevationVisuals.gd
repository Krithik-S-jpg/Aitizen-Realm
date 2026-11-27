extends RefCounted
const STEP := 36.0
const KIT = preload("res://assets/world/cohesive/terrain-kit-v2.png")
const Style = preload("res://scripts/world/RealmStyle.gd")

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
		var tint := Style.ROCK_LIGHT if edge == 0 else Style.ROCK_SHADE
		var u := float(at.x if edge == 0 else at.y)*.25
		renderer.draw_polygon(face,PackedColorArray([tint]),PackedVector2Array([Vector2(u,0),Vector2(u+.25,0),Vector2(u+.25,drop*.2),Vector2(u,drop*.2)]),renderer._ground_material("cliff-face"))
		# Bevel the exposed corner with a narrow darker facet. The grounded
		# contact edge stays aligned to navigation geometry.
		if edge == 0 and height > ground_level(renderer._tiles,at+Vector2i(0,1)):
			var corner := diamond[2]
			renderer.draw_colored_polygon(PackedVector2Array([corner-Vector2(4,2),corner+Vector2(4,-2),corner+down+Vector2(4,-2),corner+down-Vector2(4,0)]),Color("686c59"))


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
			# Broad tapered recesses break up the continuous wall face.
			for crack: int in range(2):
				var notch := a.lerp(b,.25+crack*.48)
				renderer.draw_colored_polygon(PackedVector2Array([notch,notch+Vector2(3,drop*STEP*.35),notch+down+Vector2(-2,0),notch+down+Vector2(-5,0)]),Color(.12,.15,.12,.19))
			for section: int in range(5):
				var t := float(section)/5.0
				var left := a.lerp(b,t)
				var right := a.lerp(b,t+.2)
				var depth := 2.0+float((seed+section*7)%6)
				renderer.draw_colored_polygon(PackedVector2Array([left,right,right+Vector2(-1,depth*.65),left+Vector2(1,depth)]),Style.SOD)
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
			var top := a.lerp(b,.5)
			var bottom: Vector2 = renderer.ground_to_local(at+delta)
			var side := (b-a).normalized()*9
			renderer.draw_colored_polygon(PackedVector2Array([top-side,top+side,bottom+side,bottom-side]),Color("8b8067"))
			for step: int in range(8):
				var p := top.lerp(bottom,float(step)/8)
				renderer.draw_line(p-side,p+side,Color("c2b596"),2)
				renderer.draw_line(p-side+Vector2(0,2),p+side+Vector2(0,2),Color(.20,.23,.18,.3),1)

static func illustrated(renderer,at: Vector2i,center: Vector2) -> void:
	if renderer._quality_detail_cap == 0:
		return
	var height := ground_level(renderer._tiles,at)
	var dx := height-ground_level(renderer._tiles,at+Vector2i(1,0))
	var dy := height-ground_level(renderer._tiles,at+Vector2i(0,1))
	var drop := maxi(dx,dy)
	if drop <= 0:
		return
	var data: Dictionary = renderer._tiles[at]
	var wet := str(data.get("terrain","")).to_lower() in ["water","ocean"]
	var piece := -1
	if wet and ((dx>0 and str(renderer._tiles.get(at+Vector2i(1,0),{}).get("terrain","")).to_lower() in ["water","ocean"]) or (dy>0 and str(renderer._tiles.get(at+Vector2i(0,1),{}).get("terrain","")).to_lower() in ["water","ocean"])):
		piece = 3 if drop == 1 else 4
	elif not data.get("metadata",{}).get("ramps",[]).is_empty():
		piece = 2
	elif dx>0 and dy>0:
		piece = 1
	elif str(data.get("terrain","")).to_lower() == "mountain":
		piece = 5
	elif posmod(at.x*13+at.y*7,11)==0:
		piece = 0
	if piece < 0:
		return
	var cell := Vector2(KIT.get_width()/3.0,KIT.get_height()/2.0)
	var source := Rect2(Vector2(piece%3,int(piece/3))*cell,cell)
	var size := Vector2(64,drop*STEP+32)
	# One atlas sample per selected exposed edge; geometry remains authoritative.
	renderer.draw_texture_rect_region(KIT,Rect2(center+Vector2(-size.x*.5,-17),size),source)
