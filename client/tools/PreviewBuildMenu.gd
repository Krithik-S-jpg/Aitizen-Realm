extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1152, 648)
	var template = load("res://scenes/Main.tscn").instantiate()
	var crafting = template.get_node("UI/CraftingPanel")
	crafting.get_parent().remove_child(crafting)
	template.free()
	root.add_child(crafting)
	var recipes := {}
	for kind: String in ["campfire", "shelter", "storage", "workbench", "well", "tent", "fence", "torch"]:
		recipes[kind] = {"materials": {"wood": 12, "stone": 8}, "work_required": 24}
	crafting.display_blueprints(recipes)
	crafting.open_panel()
	await create_timer(1.2).timeout
	assert(crafting.cards.get_child_count() == 8)
	assert(crafting.cards.get_parent().size.y >= 160)
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://.agent-qa/build-menu.png")
	print("PASS: eight recipe cards and usable scrolling area")
	quit()
