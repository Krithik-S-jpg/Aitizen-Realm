"""Tests for deterministic, harvestable world resource nodes."""

import pytest

from app.application.services.world_generator import WorldGenerator
from app.domain.models.resource import ResourceNode, ResourceType


def test_resource_harvest_and_depletion() -> None:
    """Harvesting is bounded by available quantity and exposes depletion."""
    resource = ResourceNode(
        resource_type=ResourceType.TREE,
        x=3,
        y=4,
        quantity=10.0,
        capacity=10.0,
    )

    assert resource.harvest(4.0) == 4.0
    assert resource.quantity == 6.0
    assert resource.harvest(20.0) == 6.0
    assert resource.depleted is True

    with pytest.raises(ValueError):
        resource.harvest(0.0)


def test_resource_placement_is_deterministic() -> None:
    """A world seed determines resource identities, positions, and quantities."""
    first = WorldGenerator.generate_terrain_world(20, 20, seed=847291)
    second = WorldGenerator.generate_terrain_world(20, 20, seed=847291)

    first_resources = [resource.model_dump() for resource in first.resources.values()]
    second_resources = [resource.model_dump() for resource in second.resources.values()]

    assert first_resources == second_resources
    assert {resource.resource_type for resource in first.resources.values()} >= {
        ResourceType.TREE,
        ResourceType.STONE,
    }


def test_world_resource_spatial_lookup() -> None:
    """Resources can be queried at a logical world coordinate."""
    world = WorldGenerator.generate_terrain_world(20, 20, seed=847291)
    resource = next(iter(world.resources.values()))

    assert resource in world.resources_at(resource.x, resource.y)
    assert world.resources_at(-100, -100) == []


def test_biological_resources_grow() -> None:
    """Plants and young trees mature while stone remains unchanged."""
    world = WorldGenerator.generate_terrain_world(20, 20, seed=847291)
    biological = next(
        resource
        for resource in world.resources.values()
        if resource.resource_type in {ResourceType.TREE, ResourceType.PLANT}
        and resource.growth < 1.0
    )
    before = biological.growth
    biological.advance_growth()
    assert biological.growth > before

    stone = next(
        resource
        for resource in world.resources.values()
        if resource.resource_type == ResourceType.STONE
    )
    stone.advance_growth()
    assert stone.growth == 1.0
