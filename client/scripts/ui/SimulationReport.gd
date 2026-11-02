extends AcceptDialog

var report_text := ""
var content: RichTextLabel
var files: FileDialog

func _ready() -> void:
	title = "Simulation report · retained history"
	var layout := VBoxContainer.new()
	add_child(layout)
	content = RichTextLabel.new()
	content.custom_minimum_size = Vector2(560, 300)
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(content)
	var download := Button.new()
	download.text = "Download report (.txt)…"
	layout.add_child(download)
	files = FileDialog.new()
	files.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	files.access = FileDialog.ACCESS_FILESYSTEM
	files.filters = PackedStringArray(["*.txt ; Text report"])
	add_child(files)
	download.pressed.connect(func() -> void:
		files.current_file = "aitizen-report.txt"
		files.popup_centered(Vector2i(680, 440)))
	files.file_selected.connect(func(path: String) -> void:
		var file := FileAccess.open(path, FileAccess.WRITE)
		if file == null:
			content.text += "\nUnable to save: " + error_string(FileAccess.get_open_error())
			return
		file.store_string(report_text)
		file.close()
		content.text += "\nSaved: " + path)

func generate(data: Dictionary) -> void:
	report_text = "AITIZEN REALM — SIMULATION REPORT\nGenerated: %s\nScope: retained history snapshot, not a full lifetime archive.\n\n" % Time.get_datetime_string_from_system()
	var events: Array = data.get("timeline", [])
	report_text += "RECORDED EVENTS: %d\n\n" % events.size()
	for event: Dictionary in events:
		report_text += "Tick %s | %s | %s\n" % [event.get("tick", "?"), event.get("type", "event"), event.get("summary", "")]
	if events.is_empty():
		report_text += "No events received. Refresh history first.\n"
	report_text += "\nECONOMY SNAPSHOT\n" + JSON.stringify(data.get("economy", {}), "  ")
	content.text = report_text
	popup_centered(Vector2i(640, 440))
