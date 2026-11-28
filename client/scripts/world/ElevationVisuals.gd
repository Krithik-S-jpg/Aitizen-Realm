extends RefCounted
const STEP := 24.0
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
		renderer._canvas().draw_polygon(face,PackedColorArray([tint]),PackedVector2Array([Vector2(u,0),Vector2(u+.25,0),Vector2(u+.25,drop*.2),Vector2(u,drop*.2)]),renderer._ground_material("cliff-face"))
		# Bevel the exposed corner with a narrow darker facet. The grounded
		# contact edge stays aligned to navigation geometry.
		if edge == 0 and height > ground_level(renderer._tiles,at+Vector2i(0,1)):
			var corner := diamond[2]
			renderer._canvas().draw_colored_polygon(PackedVector2Array([corner-Vector2(4,2),corner+Vector2(4,-2),corner+down+Vector2(4,-2),corner+down-Vector2(4,0)]),Color("686c59"))


		var tile: Dictionary = renderer._tiles[at]
		var neighbor: Dictionary = renderer._tiles.get(at+delta,{})
		var waterfall := str(tile.get("terrain","")).to_lower() in ["water","ocean"] and str(neighbor.get("terrain","")).to_lower() in ["water","ocean"]
		var ramps: Array = tile.get("metadata",{}).get("ramps",[])
		if waterfall:
			renderer._canvas().draw_colored_polygon(face,Color(.21,.60,.69,.83))
			for stream: int in range(6):
				var p := a.lerp(b,(stream+.5)/6.0)
				var phase := fposmod(float(renderer._visual_seconds)*.8+stream*.17,1)
				renderer._canvas().draw_line(p+down*phase,p+down*minf(1,phase+.32),Color(.73,.89,.85,.6),2)
			renderer._canvas().draw_line(a+down,b+down,Color(.8,.9,.85,.7),3)
			if renderer._quality_detail_cap > 0:
				for foam: int in range(5):
					var spread := fposmod(float(renderer._visual_seconds)*.35+foam*.21,1.0)
					var landing := (a+down).lerp(b+down,(foam+.5)/5.0)+Vector2(0,spread*7)
					renderer._canvas().draw_arc(landing,2+spread*5,0,PI,7,Color(.79,.89,.84,(1-spread)*.38),1)
		else:
			# A continuous biome-matched lip avoids grassy teeth on snow and rock.
			var terrain := str(tile.get("terrain","grass")).to_lower()
			var lip: Color = renderer.TERRAIN_COLORS.get(terrain,Color("859268"))
			renderer._canvas().draw_line(a,b,lip.darkened(.12),2.0)
			renderer._canvas().draw_line(a+down,b+down,Color(.12,.16,.12,.20),2.0)
		if [at.x+delta.x,at.y+delta.y] in ramps:
			var top := a.lerp(b,.5)
			var bottom: Vector2 = renderer.ground_to_local(at+delta)
			var side := (b-a).normalized()*9
			renderer._canvas().draw_colored_polygon(PackedVector2Array([top-side,top+side,bottom+side,bottom-side]),Color("8b8067"))
			for step: int in range(8):
				var p := top.lerp(bottom,float(step)/8)
				renderer._canvas().draw_line(p-side,p+side,Color("c2b596"),2)
				renderer._canvas().draw_line(p-side+Vector2(0,2),p+side+Vector2(0,2),Color(.20,.23,.18,.3),1)

static func illustrated(_renderer,_at: Vector2i,_center: Vector2) -> void:
	# Standalone atlas pieces extended beyond their tile footprints and overpainted
	# neighboring terrain. Connected textured faces now provide the rock detail.
	pass
