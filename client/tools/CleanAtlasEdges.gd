extends SceneTree

## Reproducible cleanup for generated transparent atlases. Pixels with only a
## trace of alpha carry the generator's bright RGB matte into nearest-neighbour
## rendering, so discard that fringe without touching the painted sprites.

const JOBS := [
	{
		"source": "res://assets/pixel_art/aitizen_realm_atlas_v1.png",
		"output": "res://assets/pixel_art/aitizen_realm_atlas_v1_clean.png"
	},
	{
		"source": "res://assets/pixel_art/living_biomes_atlas_v1_raw.png",
		"output": "res://assets/pixel_art/living_biomes_atlas_v1_clean.png"
	}
]
const ALPHA_CUTOFF := 0.16


func _init() -> void:
	for job: Dictionary in JOBS:
		var source := str(job["source"])
		var output := str(job["output"])
		var image := Image.load_from_file(source)
		if image.is_empty():
			push_error("Could not load %s" % source)
			quit(1)
			return
		for y: int in range(image.get_height()):
			for x: int in range(image.get_width()):
				var pixel := image.get_pixel(x, y)
				if pixel.a < ALPHA_CUTOFF:
					image.set_pixel(x, y, Color.TRANSPARENT)
		var error := image.save_png(output)
		if error != OK:
			push_error("Could not save %s" % output)
			quit(1)
			return
		print("Cleaned atlas edge alpha: %s" % output)
	quit()
