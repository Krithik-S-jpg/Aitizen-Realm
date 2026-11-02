extends Control
class_name AnalysisPanel

## Modal research/history surface; the live world remains visible beneath it.

signal refresh_requested()
signal navigation_requested(mode: String)
signal focus_requested(position: Vector2i)

var _panel: PanelContainer
var _title: Label
var _subtitle: Label
var _content: RichTextLabel
var _mode := "research"
var _tween: Tween
var _data: Dictionary = {}
var _summary: Label
var _table: Tree
var _search: LineEdit
var _sidebar: VBoxContainer
var _population_chart: Control
var _discovery_map: Control
var _migration_map: Control
var _refresh_elapsed := 0.0
var _selected_record_id := ""


func _process(delta: float) -> void:
	if not visible:
		_refresh_elapsed = 0.0
		return
	_refresh_elapsed += delta
	if _refresh_elapsed >= 3.0:
		_refresh_elapsed = 0.0
		refresh_requested.emit()


func _ready() -> void:
	_build()
	hide()


func open_mode(mode: String) -> void:
	_selected_record_id = ""
	_mode = mode
	_title.text = {"animals": "Wildlife observatory", "buildings": "Buildings & construction", "research": "Research & experiments", "history": "World history", "settlements": "Settlements & groups", "economy": "Resources & economy"}.get(mode, "Observatory")
	_subtitle.text = {"research": "Measurements and configured experiments", "history": "Recorded events from the living world", "settlements": "Emergent groups and their home territories", "economy": "Stored materials and construction activity"}.get(mode, "")
	_build_sidebar()
	if mode == "expeditions":
		_title.text = "Expeditions & shared knowledge"
		_subtitle.text = "Live parties, provisions, discoveries and return reports"
	if mode == "discoveries":
		_title.text = "The Discovery Journal"
		_subtitle.text = "Observed places · physical evidence · shared knowledge"
	_content.text = "[color=#72d6bb]Synchronizing authoritative simulation data…[/color]"
	show()
	_panel.modulate.a = 0.0
	_panel.scale = Vector2(0.97, 0.97)
	_panel.pivot_offset = _panel.size * 0.5
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_QUART).set_ease(Tween.EASE_OUT)
	_tween.tween_property(_panel, "modulate:a", 1.0, 0.2)
	_tween.tween_property(_panel, "scale", Vector2.ONE, 0.26)
	refresh_requested.emit()


func close_panel() -> void:
	if not visible:
		return
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	_tween.tween_property(_panel, "modulate:a", 0.0, 0.15)
	_tween.tween_property(_panel, "scale", Vector2(0.98, 0.98), 0.15)
	_tween.chain().tween_callback(hide)


func display_observation(data: Dictionary) -> void:
	_data = data
	_render_data()


func _build_sidebar() -> void:
	for child: Node in _sidebar.get_children():
		_sidebar.remove_child(child)
		child.queue_free()
	for mode: String in ["animals", "buildings", "research", "history", "settlements", "economy", "expeditions", "discoveries"]:
		var button := Button.new()
		button.text = {"animals": "Wildlife & habitats", "buildings": "Construction sites", "research": "Research overview", "history": "Event timeline", "settlements": "Groups & homes", "economy": "Material stock", "expeditions": "Expeditions", "discoveries": "Discovery journal"}[mode]
		button.custom_minimum_size = Vector2(170, 38)
		button.toggle_mode = true
		button.button_pressed = mode == _mode
		button.pressed.connect(func() -> void: navigation_requested.emit(mode))
		_sidebar.add_child(button)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(_sidebar)


func _render_data() -> void:
	_table.clear()
	var tree_root := _table.create_item()
	var records: Array = []
	var headings: Array = []
	match _mode:
		"discoveries":
			headings = ["Discovered place", "Evidence", "First observer"]
			for entry: Dictionary in _data.get("discovery_journal", []):
				var observers: Array = entry.get("discoverers", [])
				records.append([entry.get("name", "Unknown ruin"), "Inspected" if entry.get("inspected", false) else "Unexamined", observers[0].get("name", "Unknown") if not observers.is_empty() else "Unknown", entry])
			_content.text = "Select a discovery to read its evidence and provenance. Double-click to focus its location. Undiscovered sites remain hidden."
		"expeditions":
			headings = ["Party", "Stage / destination", "Reason"]
			for trip: Dictionary in _data.get("expeditions", []):
				records.append([", ".join(trip.get("member_names", [])), "%s · %s" % [trip.get("phase", ""), str(trip.get("destination", []))], trip.get("reason", ""), trip])
			_content.text = "Short supply-checked surveys. Select a party to inspect discoveries, carried supplies and return status."
		"animals":
			headings = ["Animal", "Activity / age", "Health / position"]
			for animal: Dictionary in _data.get("wildlife", []):
				var metadata: Dictionary = animal.get("metadata", {})
				var needs: Dictionary = animal.get("needs", {}) if animal.get("needs") is Dictionary else {}
				records.append([str(animal.get("name", "Animal")), "%s · %s days" % [metadata.get("state", "idle"), metadata.get("age_days", "unknown")], "%s HP · (%s, %s)" % [needs.get("health", "—"), animal.get("x", 0), animal.get("y", 0)], animal])
			_content.text = "Select an animal for its observed lifestyle, territory and family. Double-click a row to focus its location."
			for entry: Dictionary in _data.get("wildlife_journal", []):
				records.append(["FIELD NOTE · " + str(entry.get("species", "Wildlife")), str(entry.get("kind", "sighting")).replace("_", " "), "Seen by %s · T%s" % [entry.get("observer", ""), entry.get("last_seen_tick", 0)], entry])
		"buildings":
			headings = ["Building", "Completion", "Position / supplies"]
			for site: Dictionary in _data.get("buildings", []):
				records.append([str(site.get("structure_type", "Building")).capitalize(), "%d%%" % roundi(float(site.get("progress_ratio", 0)) * 100), "(%s, %s) · fuel %.1f" % [site.get("x", 0), site.get("y", 0), float(site.get("fuel", 0))], site])
			_content.text = "Select a site to inspect actual construction work, fuel, crops and stockpile. Double-click to focus the world."
		"history":
			headings = ["Tick", "Event", "Details"]
			for event: Dictionary in _data.get("timeline", []):
				records.append([str(event.get("tick", "—")), str(event.get("type", "Event")).capitalize(), str(event.get("summary", ""))])
			_content.text = "Events reflect the retained simulation history."
		"settlements":
			headings = ["Group", "Members", "Home territory"]
			for group: Dictionary in _data.get("settlements", _data.get("groups", [])):
				records.append([str(group.get("name", "Group")), str(group.get("active_members", group.get("member_ids", []).size())), "%s, %s" % [group.get("home_x", "—"), group.get("home_y", "—")], group])
			_content.text = "Select a settlement for shortages, assigned work, supplies and construction. Refreshes every 3 seconds while open."
		"economy":
			headings = ["Material", "Stored quantity", "Source"]
			var economy: Dictionary = _data.get("economy", {})
			var stock: Dictionary = economy.get("stock", {})
			for material_key: String in stock:
				records.append([material_key.capitalize(), "%.1f" % float(stock[material_key]), "Carried + communal storage"])
			_content.text = "Stored supplies across %s inventories. %s / %s structures complete.\nMarket prices and trade routes are not yet simulated." % [economy.get("inventories", 0), economy.get("completed_structures", 0), economy.get("structures", 0)]
		_:
			headings = ["Experiment", "Status", "Seed"]
			for experiment: Dictionary in _data.get("experiments", []):
				records.append([str(experiment.get("name", "Experiment")), str(experiment.get("status", "Draft")), str(experiment.get("seed", "—"))])
			_content.text = _research_text(_data)
	_table.columns = 3
	for index: int in range(3):
		_table.set_column_title(index, headings[index])
	var shown := 0
	for record: Array in records:
		if not _search.text.is_empty() and not str(record).to_lower().contains(_search.text.to_lower()):
			continue
		var item := _table.create_item(tree_root)
		if record.size() > 3:
			item.set_metadata(0, record[3])
			if str(record[3].get("id", "")) == _selected_record_id and not _selected_record_id.is_empty():
				item.select(0)
		for index: int in range(3):
			item.set_text(index, str(record[index]))
		shown += 1
	_summary.text = "%d records   ·   %s" % [shown, "No matching records" if shown == 0 else "Live simulation data"]
	_population_chart.visible = _mode in ["research", "settlements"]
	_discovery_map.visible = _mode == "discoveries"
	_migration_map.hide()
	_table.custom_minimum_size.y = 110 if _mode == "discoveries" else 0
	_content.custom_minimum_size.y = 100 if _mode == "discoveries" else 130
	_discovery_map.set_entries(_data.get("discovery_journal", []), _selected_record_id)
	_population_chart.set_samples(_data.get("metrics", []))
	_inspect_record()


func _inspect_record() -> void:
	var item := _table.get_selected()
	if item == null or not item.get_metadata(0) is Dictionary:
		return
	var record: Dictionary = item.get_metadata(0)
	_migration_map.visible = _mode == "animals" and record.get("kind", "") == "migration_sightings"
	if _migration_map.visible:
		_migration_map.set_points(record.get("points", []))
	_selected_record_id = str(record.get("id", ""))
	if _mode == "discoveries":
		_discovery_map.set_entries(_data.get("discovery_journal", []), _selected_record_id)
		var lines: Array[String] = [str(record.get("name", "")), str(record.get("mystery", "")), "EVIDENCE: " + str(record.get("evidence", "Approach this site to inspect the inscription.")), "ARTIFACT: " + str(record.get("artifact", "Not yet examined"))]
		for observer: Dictionary in record.get("discoverers", []):
			lines.append("Observed by %s · tick %s" % [observer.get("name", ""), observer.get("tick", 0)])
		for account: Dictionary in record.get("accounts", []):
			lines.append("%s · %s · %.0f%% confidence" % [account.get("citizen", ""), account.get("source", ""), float(account.get("confidence", 0)) * 100])
		lines.append("Expedition accounts: " + str(record.get("expeditions", [])))
		for comment: Dictionary in record.get("interpretations", []):
			lines.append("INTERPRETATION (not a fact) · %s: %s" % [comment.get("speaker", ""), comment.get("text", "")])
		_content.text = "\n".join(lines).replace("[", "[lb]")
		return
	if _mode == "expeditions":
		var lines: Array[String] = ["PARTY: " + ", ".join(record.get("member_names", [])), "STAGE: " + str(record.get("phase", "")), "DESTINATION: " + str(record.get("destination", [])), "RETURN REASON: " + str(record.get("reason", "")), "CARRIED SUPPLIES"]
		for member: String in record.get("supplies", {}):
			lines.append(str(record.supplies[member]))
		lines.append("ITINERARY: " + str(record.get("kind", "survey")))
		if record.has("camp"):
			lines.append("OVERNIGHT CAMP: %s · Rest completed: %s" % [str(record.camp), str(record.get("overnight_complete", false))])
		lines.append("PLANNER: " + str(record.get("planner", "utility")))
		lines.append("EQUIPMENT STILL NEEDED: " + str(record.get("equipment", {})))
		if record.has("rescue"):
			lines.append("CASUALTY RETRIEVAL: " + str(record.rescue))
		lines.append("DISCOVERIES")
		for member: String in record.get("discoveries", {}):
			lines.append("%d newly observed resource locations" % record.discoveries[member].size())
		lines.append("Reports delivered: %d" % record.get("reports", []).size())
		_content.text = "\n".join(lines)
		return
	if _mode == "settlements":
		var lines: Array[String] = [str(record.get("name", "Settlement")), "SHORTAGES"]
		for shortage: String in record.get("shortages", []):
			lines.append("• " + shortage)
		if record.get("shortages", []).is_empty():
			lines.append("No monitored shortage detected.")
		lines.append("STORED: %s\nCARRIED: %s\nWORKERS" % [str(record.get("stock", {})), str(record.get("carried", {}))])
		lines.append("HOMES: %d · BEDS: %d total / %d available" % [record.get("households", []).size(), int(record.get("beds_total", 0)), int(record.get("beds_available", 0))])
		for job: Dictionary in record.get("jobs", []):
			lines.append("%s · %s — %s" % [job.get("name", "Citizen"), job.get("activity", "idle"), job.get("reason", "")])
		lines.append("JOB BOARD")
		for task: Dictionary in record.get("job_board", []):
			lines.append("%s · %s%s — %s" % [str(task.get("status", "open")).to_upper(), task.get("job_type", "task"), " · " + str(task.get("material")) if task.get("material") else "", task.get("reason", "")])
		lines.append("CONSTRUCTION")
		lines.append("FOOD RESERVE: %.1f / %.1f target" % [float(record.get("food_available", 0)), float(record.get("reserve_target", 0))])
		for repair: Dictionary in record.get("maintenance", []):
			lines.append("Maintenance: %s · %.0f%% condition" % [repair.get("type", "Building"), float(repair.get("condition", 100))])
		lines.append("VILLAGE STORY")
		var project: Dictionary = record.get("community_project", {})
		if not project.is_empty():
			lines.append("PROJECT: %s · %s · %d supporters" % [project.get("title", ""), project.get("status", ""), project.get("votes", []).size()])
		for care: Dictionary in record.get("care_jobs", []):
			lines.append("%s · %s" % [care.get("citizen", "Citizen"), care.get("kind", "Care job")])
		for event: Dictionary in record.get("story", []):
			lines.append("T%d · %s" % [int(event.get("tick", 0)), event.get("text", "")])
		for site: Dictionary in record.get("construction", []):
			lines.append("%s · %d%% · %s" % [site.get("type", "Site"), roundi(float(site.get("progress", 0)) * 100), "funded" if site.get("funded", false) else "needs " + str(site.get("missing_materials", {}))])
		_content.text = "\n".join(lines)
	if _mode == "animals":
		if record.has("observer"):
			_content.text = "%s · %s\nObserved by %s at (%s, %s)\nFirst sighting T%s · Last sighting T%s\nStatus: %s · Eggs: %s\nObserved route points: %s\nThis is a past observation, not live knowledge of unseen wildlife." % [record.get("species", ""), record.get("kind", ""), record.get("observer", ""), record.get("x", 0), record.get("y", 0), record.get("first_seen_tick", 0), record.get("last_seen_tick", 0), record.get("status", "sighting"), record.get("eggs", 0), str(record.get("points", []))]
			return
		var metadata: Dictionary = record.get("metadata", {})
		_content.text = "%s\n%s\nHome: (%s, %s) · Stage: %s\nMother: %s · Offspring: %s" % [record.get("name", "Animal"), metadata.get("lifestyle", "No lifestyle observation yet"), metadata.get("home_x", "—"), metadata.get("home_y", "—"), metadata.get("age_stage", "unknown"), metadata.get("mother_id", "Unknown"), metadata.get("offspring_count", 0)]
	elif _mode == "buildings":
		_content.text = "%s\nWork: %.1f / %.1f\nSupplied: %s\nStill needed: %s\nBeds: %s · Residents: %s\nStockpile: %s\nFuel: %.1f · Ripe food: %.1f" % [record.get("structure_type", "Building"), float(record.get("progress", 0)), float(record.get("work_required", 0)), str(record.get("materials_delivered", {})), str(record.get("missing_materials", {})), record.get("bed_capacity", 0), record.get("resident_ids", []).size(), str(record.get("stockpile", {}).get("items", {})), float(record.get("fuel", 0)), float(record.get("crop_food", 0))]


func display_error(message: String) -> void:
	_content.text = "[color=#e98a7b]UNAVAILABLE[/color]\n\n%s" % message


func _research_text(data: Dictionary) -> String:
	var metrics: Array = data.get("metrics", [])
	var experiments: Array = data.get("experiments", [])
	var world: Dictionary = data.get("world", {})
	var lines: Array[String] = [
		"[color=#72d6bb][b]CURRENT RESEARCH STATE[/b][/color]",
		"World seed: %s   Bounds: %s × %s   Chunks: %s" % [world.get("seed", "N/A"), world.get("width", "N/A"), world.get("height", "N/A"), world.get("chunks", "N/A")],
		"",
		"[b]METRICS[/b]"
	]
	if metrics.is_empty():
		lines.append("No completed tick measurements yet. Start or step the simulation.")
	else:
		var latest: Dictionary = metrics[-1]
		lines.append("Tick %d   Population %d   Groups %d   Structures %d" % [int(latest.get("tick", 0)), int(latest.get("population", 0)), int(latest.get("groups", 0)), int(latest.get("structures", 0))])
		lines.append("Average health %.1f   Average hunger %.1f   Resources %.1f" % [float(latest.get("average_health", 0.0)), float(latest.get("average_hunger", 0.0)), float(latest.get("resources_available", 0.0))])
	lines.append("\n[b]EXPERIMENTS  %d[/b]" % experiments.size())
	for experiment: Dictionary in experiments.slice(maxi(0, experiments.size() - 8)):
		lines.append("• %s   %s   seed %s" % [experiment.get("name", "Unnamed"), experiment.get("status", "DRAFT"), experiment.get("seed", "N/A")])
	return "\n".join(lines)


func _history_text(data: Dictionary) -> String:
	var timeline: Array = data.get("timeline", [])
	var lines: Array[String] = ["[color=#e5c574][b]RECORDED TIMELINE[/b][/color]"]
	if timeline.is_empty():
		lines.append("\nNo historical episodes have been recorded yet.")
		return "\n".join(lines)
	for index in range(maxi(0, timeline.size() - 30), timeline.size()):
		var event: Dictionary = timeline[index]
		lines.append("[color=#72d6bb]T%05d[/color]  %s  —  %s" % [int(event.get("tick", 0)), str(event.get("type", "event")).to_upper(), event.get("summary", "")])
	return "\n".join(lines)


func _build() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.offset_left = 18.0
	_panel.offset_top = 76.0
	_panel.offset_right = -18.0
	_panel.offset_bottom = -18.0
	var style := StyleBoxFlat.new()
	style.bg_color = Color("07151ded")
	style.border_color = Color("347080")
	style.set_border_width_all(1)
	style.set_corner_radius_all(14)
	style.shadow_color = Color(0, 0, 0, 0.5)
	style.shadow_size = 12
	_panel.add_theme_stylebox_override("panel", style)
	add_child(_panel)
	var margin := MarginContainer.new()
	for side in ["margin_left", "margin_top", "margin_right", "margin_bottom"]:
		margin.add_theme_constant_override(side, 22)
	_panel.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	margin.add_child(column)
	var header := HBoxContainer.new()
	column.add_child(header)
	var titles := VBoxContainer.new()
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(titles)
	_title = Label.new()
	_title.add_theme_font_size_override("font_size", 23)
	_title.add_theme_color_override("font_color", Color("e8e0cf"))
	titles.add_child(_title)
	_subtitle = Label.new()
	_subtitle.add_theme_color_override("font_color", Color("91a8af"))
	titles.add_child(_subtitle)
	var refresh := Button.new()
	refresh.text = "↻  REFRESH"
	refresh.pressed.connect(func() -> void: refresh_requested.emit())
	header.add_child(refresh)
	var report := preload("res://scripts/ui/SimulationReport.gd").new()
	add_child(report)
	var report_button := Button.new()
	report_button.text = "Report / download"
	header.add_child(report_button)
	report_button.pressed.connect(func() -> void: report.generate(_data))
	var close := Button.new()
	close.text = "×  CLOSE"
	close.pressed.connect(close_panel)
	header.add_child(close)
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 18)
	column.add_child(body)
	_sidebar = VBoxContainer.new()
	body.add_child(_sidebar)
	var workspace := VBoxContainer.new()
	workspace.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(workspace)
	_search = LineEdit.new()
	_search.placeholder_text = "Search this page…"
	_search.text_changed.connect(func(_text: String) -> void: _render_data())
	workspace.add_child(_search)
	_summary = Label.new()
	_summary.text = "Waiting for observations"
	workspace.add_child(_summary)
	_table = Tree.new()
	_table.hide_root = true
	_table.column_titles_visible = true
	_table.size_flags_vertical = Control.SIZE_EXPAND_FILL
	workspace.add_child(_table)
	_table.item_selected.connect(_inspect_record)
	_table.item_activated.connect(func() -> void:
		var item := _table.get_selected()
		if item != null and item.get_metadata(0) is Dictionary:
			var record: Dictionary = item.get_metadata(0)
			focus_requested.emit(Vector2i(int(record.get("x", 0)), int(record.get("y", 0))))
			navigation_requested.emit("world")
	)
	_population_chart = preload("res://scripts/ui/PopulationChart.gd").new()
	workspace.add_child(_population_chart)
	_discovery_map = preload("res://scripts/ui/DiscoveryMap.gd").new()
	workspace.add_child(_discovery_map)
	_migration_map = preload("res://scripts/ui/MigrationMap.gd").new()
	_migration_map.hide()
	workspace.add_child(_migration_map)
	_content = RichTextLabel.new()
	_content.bbcode_enabled = true
	_content.custom_minimum_size.y = 130
	_content.add_theme_font_size_override("normal_font_size", 14)
	_content.add_theme_constant_override("line_separation", 6)
	workspace.add_child(_content)
	preload("res://scripts/ui/AtlasTheme.gd").apply_to(self)
