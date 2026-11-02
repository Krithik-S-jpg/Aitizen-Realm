import pytest
from tests.test_decisions import _systems
from app.application.services.communication_service import CommunicationService
from app.application.services.memory_service import MemoryService
from app.domain.models.entity import EntityKind


def setup_chat():
    entities, decisions, _ = _systems()
    a = entities.create(EntityKind.AGENT, "Alice", 5, 5, tags={"autonomous"})
    b = entities.create(EntityKind.AGENT, "Ben", 6, 5, tags={"autonomous"})
    world = decisions._require_world()
    service = CommunicationService(decisions._repository, MemoryService(decisions._repository))
    return world, a, b, service


def test_autonomous_food_sharing_conserves_items_and_records_chat():
    world, a, b, service = setup_chat()
    world.inventories[str(a.id)].add("food", 6)
    b.needs.hunger = 60
    service.advance_all(1)
    assert world.inventories[str(a.id)].items["food"] == 6
    assert len(world.messages) == 2  # Request and agreement precede the handoff.
    service.advance_all(2)
    assert world.inventories[str(a.id)].items["food"] == 4
    assert world.inventories[str(b.id)].items["food"] == 2
    assert len(world.messages) == 4
    assert "take 2 food" in a.metadata["conversation"][2]["content"]
    service.advance_all(2)
    assert len(world.messages) == 4


def test_gift_rejects_distance_capacity_and_invalid_amount_without_loss():
    world, a, b, service = setup_chat()
    source = world.inventories[str(a.id)]
    source.add("wood", 8)
    b.x = 12
    with pytest.raises(ValueError):
        service.give(a.id, b.id, "wood", 2, 1)
    b.x = 6
    world.inventories[str(b.id)].capacity = 1
    for amount in (2, float("nan"), -1):
        with pytest.raises(ValueError):
            service.give(a.id, b.id, "wood", amount, 1)
    assert source.items["wood"] == 8
    assert not world.messages
