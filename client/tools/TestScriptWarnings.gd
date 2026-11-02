extends SceneTree
## Compile every application script with the screenshot's warning categories enforced.
func _initialize() -> void:
	for warning in ["incompatible_ternary", "shadowed_variable", "shadowed_variable_base_class"]:
		ProjectSettings.set_setting("debug/gdscript/warnings/" + warning, 2)
	var failures := _check_directory("res://scripts")
	print("Script warning audit: %d failures" % failures)
	quit(1 if failures else 0)

func _check_directory(path: String) -> int:
	var failures := 0
	for directory in DirAccess.get_directories_at(path):
		failures += _check_directory(path.path_join(directory))
	for filename in DirAccess.get_files_at(path):
		if not filename.ends_with(".gd"):
			continue
		var script := load(path.path_join(filename)) as GDScript
		if script == null or script.reload() != OK:
			printerr("Failed script: " + path.path_join(filename))
			failures += 1
	return failures
