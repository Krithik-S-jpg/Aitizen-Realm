extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var visuals = load("res://scripts/world/CitizenVisuals.gd")
	for avatar: String in ["adult_male","adult_female"]:
		var texture: Texture2D = visuals.texture(avatar)
		assert(texture != null)
		for action: String in ["idle","move","carry","build","sleep","gather"]:
			var frames: Array = visuals.action_frames(avatar,action)
			assert(frames.size()==8)
			for frame: Array in frames:
				assert(Rect2(Vector2.ZERO,texture.get_size()).encloses(Rect2(frame[0],frame[1],frame[2],frame[3])))
				assert(frame[1]==frames[0][1],"Shared row origin preserves body scale")
		assert(visuals.action_frames(avatar,"carry") != visuals.action_frames(avatar,"move"),"Carry has dedicated leg and arm frames")
		var idle: Array = visuals.action_frames(avatar,"idle")[0]
		var portrait := texture.get_image().get_region(Rect2i(idle[0],idle[1],idle[2],idle[3]))
		portrait.save_png("res://../backend/app/player_portraits/%s.png" % avatar)
	assert(not visuals.action_frames("scout","move").is_empty(),"Legacy avatars still load after new bases")
	assert(WorldRenderer.animation_frame(0,8,.8)==0)
	assert(WorldRenderer.animation_frame(.4,8,.8)==4)
	print("PASS: adult atlas bounds, pivots, carry frames, legacy compatibility and cycle timing")
	quit()
