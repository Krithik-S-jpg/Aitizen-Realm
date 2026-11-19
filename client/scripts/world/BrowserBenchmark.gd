extends Node2D
## Explicit ?renderer_benchmark=1 diagnostic; synthetic, no backend mutation.
var renderer: WorldRenderer
var entities: Array = []
var samples: Array[float] = []
var frame := 0
var previous := 0
var label: Label
var quality := "balanced"

func _ready() -> void:
	var camera := Camera2D.new()
	camera.position = get_viewport_rect().size * 0.5
	add_child(camera)
	camera.make_current()
	renderer = WorldRenderer.new()
	renderer.position = Vector2(576,-100)
	add_child(renderer)
	quality = str(JavaScriptBridge.eval("new URLSearchParams(location.search).get('quality') || 'balanced'")) if OS.has_feature("web") else "balanced"
	renderer.set_visual_quality(quality)
	var tiles := {}
	for x: int in range(48):
		for y: int in range(48):
			tiles[Vector2i(x,y)] = {"terrain":"water" if x%17 < 3 else "grass","metadata":{}}
	var resources: Array = []
	for i: int in range(240):
		resources.append({"id":str(i),"x":(i*17)%48,"y":(i*29 + i/48*7)%48,"type":"tree","growth":0.8,"variant":i%3})
	var structures: Array = []
	for i: int in range(16):
		structures.append({"id":str(i),"x":8+i%4*3,"y":8+i/4*3,"structure_type":"shelter","completed":true})
	for i: int in range(32):
		entities.append({"id":"bench%d"%i,"x":7+i%8,"y":10+i/8,"kind":"agent","avatar_id":"rowan" if i%2 else "juniper","action":"move","metadata":{}})
	renderer.render_world(tiles,resources,structures,entities)
	renderer.configure_environment({"weather":"RAIN","weather_intensity":0.6,"wind_speed":10,"wind_direction":60})
	var rain := WeatherOverlay.new()
	rain.renderer = renderer
	renderer.add_child(rain)
	rain.set_visual_quality(quality)
	rain.configure("RAIN",0.6,10,60,Vector2(0,500),24,64,32)
	label = Label.new()
	label.position = Vector2(20,20)
	label.text = "Browser benchmark · warming up · synthetic world"
	label.add_theme_color_override("font_color",Color.BLACK)
	add_child(label)
	previous = Time.get_ticks_usec()

func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	if frame >= 60:
		samples.append((now-previous)/1000.0)
	previous = now
	frame += 1
	renderer.position.x = 576 + sin(frame*0.01)*100
	if frame%24 == 0:
		for entity: Dictionary in entities:
			entity.x += 1 if frame%48 == 0 else -1
		renderer.update_entities(entities)
	if frame == 360:
		var total := 0.0
		for value: float in samples:
			total += value
		samples.sort()
		var result := {"fps":300000.0/total,"median_ms":samples[150],"p95_ms":samples[285],"worst_ms":samples.back(),"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"quality":quality,"citizens":32,"homes":16,"rain":true,"camera_pan":true}
		label.text = "Synthetic browser benchmark complete\n"+JSON.stringify(result)
		print("BROWSER_PERF "+JSON.stringify(result))
		set_process(false)
