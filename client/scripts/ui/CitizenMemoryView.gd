extends AcceptDialog
## Edges represent recorded relationships, not inferred causes.
var _graph: GraphEdit
var _serial := 0

func _ready() -> void:
	title = "Citizen memory · important experiences"
	min_size = Vector2i(680, 420)
	unresizable = false
	_graph = GraphEdit.new()
	_graph.custom_minimum_size = Vector2(650, 370)
	_graph.minimap_enabled = true
	add_child(_graph)

func _node(heading: String, body: String, at: Vector2, tint: Color) -> GraphNode:
	var node := GraphNode.new()
	node.name = "Memory%d" % _serial
	_serial += 1
	node.title = heading
	node.position_offset = at
	node.custom_minimum_size.x = 240
	var label := Label.new()
	label.text = body
	label.custom_minimum_size.x = 220
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	node.add_child(label)
	node.set_slot(0, true, 0, tint, true, 0, tint)
	_graph.add_child(node)
	return node

func _link(parent: GraphNode, child: GraphNode) -> void:
	_graph.connect_node(parent.name, 0, child.name, 0)

func show_citizen(citizen: Dictionary) -> void:
	_graph.clear_connections()
	for child in _graph.get_children():
		if child is GraphNode:
			_graph.remove_child(child)
			child.queue_free()
	_serial = 0
	var mint := Color("72d9bd")
	var gold := Color("e7c97a")
	var coral := Color("ef927e")
	var identity := _node(str(citizen.get("name", "Citizen")), "PERSONAL MEMORY\nCurrent fear: %.0f / 100\n\nDrag nodes to arrange. Pan and zoom to explore.\nEdges connect experiences to recorded details." % float(citizen.get("fear", 0)), Vector2(40, 80), mint)
	var episodes: Array = citizen.get("memory_graph", [])
	if episodes.is_empty():
		_link(identity, _node("No important memories yet", "Shows danger, significant discoveries or communication, and successful building/crafting. Routine actions are hidden, not deleted.", Vector2(360, 80), gold))
	var row := 0.0
	for index: int in range(episodes.size() - 1, -1, -1):
		var episode: Dictionary = episodes[index]
		var detail: Dictionary = episode.get("details", {})
		var experience := _node("Tick %d · Experience" % int(episode.get("tick", 0)), "%s\n\nPlace: (%d, %d)\nImportance: %.0f%%" % [episode.get("summary", "Experience"), int(episode.get("x", 0)), int(episode.get("y", 0)), float(episode.get("importance", 0)) * 100], Vector2(360, 80 + row), coral if detail.has("species") else gold)
		_link(identity, experience)
		if detail.has("species"):
			_link(experience, _node("Encounter · " + str(detail.get("experience", "observed")), "%s attack\nAttacker: %s\nVictim: %s" % [detail["species"], detail.get("attacker_name", detail.get("attacker_id", "unknown")), detail.get("victim_name", detail.get("victim_id", "unknown"))], Vector2(690, 80 + row), coral))
			var emotion := _node("Emotional consequence", "+%s fear when recorded\nFear fades with time.\n\n%s" % [detail.get("fear_gain", 0), detail.get("consequence", "")], Vector2(690, 290 + row), mint)
			_link(experience, emotion)
			var metadata: Dictionary = citizen.get("metadata", {})
			if metadata.get("fear_memory_id", "") == episode.get("id", ""):
				_link(emotion, _node("Current decision", str(citizen.get("decision_reason", "Not reported")), Vector2(1020, 290 + row), mint))
			row += 450
		else:
			if not detail.is_empty():
				_link(experience, _node("Recorded details", JSON.stringify(detail, "  "), Vector2(690, 80 + row), mint))
			row += 280
	_graph.zoom = 0.85
	_graph.scroll_offset = Vector2.ZERO
	var available := DisplayServer.window_get_size()
	popup_centered(Vector2i(mini(1120, available.x - 40), mini(700, available.y - 60)))
