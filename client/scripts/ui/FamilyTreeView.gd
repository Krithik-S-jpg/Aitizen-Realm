extends AcceptDialog

func show_family(citizen: Dictionary, citizens: Array) -> void:
	title = "Family relationships"
	for child in get_children():
		if child is GraphEdit:
			remove_child(child)
			child.queue_free()
	var graph := GraphEdit.new()
	graph.custom_minimum_size = Vector2(720, 420)
	graph.minimap_enabled = false
	add_child(graph)
	var people: Dictionary = {}
	for person: Dictionary in citizens:
		people[str(person.id)] = person
	var metadata: Dictionary = citizen.get("metadata", {})
	var center := _node(graph, citizen, Vector2(230, 150), "Selected citizen")
	var parent_ids: Array = metadata.get("parent_ids", [])
	for index in range(parent_ids.size()):
		var parent: Dictionary = people.get(str(parent_ids[index]), {"id": parent_ids[index], "name": "Parent (not in active registry)"})
		var node := _node(graph, parent, Vector2(30 + index * 270, 15), "Parent")
		graph.connect_node(node.name, 0, center.name, 0)
	var partner_id := str(metadata.get("partner_id", ""))
	if people.has(partner_id):
		var partner := _node(graph, people[partner_id], Vector2(500, 150), "Partner")
		graph.connect_node(center.name, 0, partner.name, 0)
	var index := 0
	for person: Dictionary in citizens:
		if str(citizen.id) in person.get("metadata", {}).get("parent_ids", []):
			var node := _node(graph, person, Vector2(20 + index * 240, 310), "Child")
			graph.connect_node(center.name, 0, node.name, 0)
			index += 1
	popup_centered(Vector2i(780, 500))

func _node(graph: GraphEdit, person: Dictionary, position: Vector2, relation: String) -> GraphNode:
	var node := GraphNode.new()
	node.name = "Person" + str(graph.get_child_count())
	node.title = str(person.get("name", "Citizen"))
	node.position_offset = position
	var label := Label.new()
	label.text = relation + "\n" + str(person.get("metadata", {}).get("life_stage", "Age not recorded"))
	node.add_child(label)
	node.set_slot(0, true, 0, Color("65d6c0"), true, 0, Color("65d6c0"))
	graph.add_child(node)
	return node
