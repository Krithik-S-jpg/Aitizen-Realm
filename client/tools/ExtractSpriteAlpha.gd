extends SceneTree

const JOBS := [
	{
		"source": "res://assets/pixel_art/aitizen_character_actions_v4_24f_chroma.png",
		"output": "res://assets/pixel_art/aitizen_character_actions_v4_24f_clean.png"
	},
	{
		"source": "res://assets/pixel_art/wildlife_actions_v4_primary_chroma.png",
		"output": "res://assets/pixel_art/wildlife_actions_v4_primary_clean.png"
	},
	{
		"source": "res://assets/pixel_art/wildlife_actions_v4_secondary_chroma.png",
		"output": "res://assets/pixel_art/wildlife_actions_v4_secondary_clean.png"
	}
]


func _init() -> void:
	for job: Dictionary in JOBS:
		var source := str(job["source"])
		var output := str(job["output"])
		var image := Image.load_from_file(source)
		if image.is_empty():
			push_error("Could not load %s" % source)
			quit(1)
			return
		image.convert(Image.FORMAT_RGBA8)
		_extract_chroma_key(image)
		if image.get_pixel(0, 0).a > 0.01:
			push_error("Chroma cleanup left an opaque atlas corner in %s" % source)
			quit(1)
			return
		if image.save_png(output) != OK:
			push_error("Could not save %s" % output)
			quit(1)
			return
		print("Extracted sprite alpha: %s" % output)
	quit()


func _extract_chroma_key(image: Image) -> void:
	var width := image.get_width()
	var height := image.get_height()
	for y: int in range(height):
		for x: int in range(width):
			var pixel := image.get_pixel(x, y)
			var magenta_strength := minf(pixel.r, pixel.b) - pixel.g
			if magenta_strength > 0.16 and pixel.r + pixel.b > 0.65:
				image.set_pixel(x, y, Color.TRANSPARENT)
