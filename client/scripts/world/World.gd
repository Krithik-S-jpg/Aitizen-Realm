# World.gd
extends Node2D

## Handles the orchestration of world data drawing inside the World Node.

@onready var renderer: WorldRenderer = $TileMap

## Triggers visual tile placement inside the nested TileMap.
func render_parsed_world(parsed_world: Dictionary) -> void:
	renderer.render_world(parsed_world["tiles"])
