from app.application.services.communication_service import CommunicationService
from app.application.services.community_routines import advance_routine
from app.application.services.memory_service import MemoryService
from app.application.services.society_service import SocietyService
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_decisions import _systems


def community():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    a = entities.create(EntityKind.AGENT, "Same name", 5, 5, tags={"autonomous"})
    b = entities.create(EntityKind.AGENT, "Same name", 7, 5, tags={"autonomous"})
    for actor in (a, b):
        decisions._perception.observe(actor.id, 0)
    service = CommunicationService(decisions._repository, MemoryService(decisions._repository), SocietyService(decisions._repository))
    return world, a, b, decisions, service


def test_promised_delivery_walks_and_survives_save_load_without_duplicate_gifts():
    world, a, b, decisions, service = community()
    world.inventories[str(a.id)].add("food", 6)
    b.needs.hunger = 60
    service.advance_all(1)
    assert a.metadata["community_task"]["kind"] == "delivery"
    assert world.inventories[str(b.id)].carried == 0
    assert advance_routine(decisions, world, a, 2, [])
    assert world.movement_plans[str(a.id)].path
    decisions._navigation.advance_all(3)
    # The persistence representation includes the in-flight commitment and route.
    restored = World.model_validate_json(world.model_dump_json())
    decisions._repository.save(restored)
    service.advance_all(4)
    service.advance_all(4)
    assert restored.inventories[str(a.id)].items["food"] == 4
    assert restored.inventories[str(b.id)].items["food"] == 2
    assert restored.entities[str(a.id)].metadata["last_community_task"]["status"] == "Delivered"
    assert restored.social_bonds[f"{b.id}:{a.id}"].trust > .1
    assert restored.entities[str(a.id)].metadata["conversation"][0]["sender_id"] == str(b.id)
    assert any(e.importance >= .8 for e in restored.episodes[str(b.id)])


def test_danger_cancels_delivery_without_inventory_transfer():
    world, a, b, decisions, service = community()
    world.inventories[str(a.id)].add("food", 6)
    b.needs.hunger = 60
    service.advance_all(1)
    assert not advance_routine(decisions, world, a, 2, [(4, 4)])
    assert "community_task" not in a.metadata
    assert world.inventories[str(a.id)].items["food"] == 6


def test_meal_requires_lit_known_fire_and_consumes_real_food_once():
    world, a, b, decisions, service = community()
    fire = Structure(structure_type=StructureType.CAMPFIRE, x=6, y=5,
                     builder_id=str(a.id), work_required=1, progress=1, fuel=5)
    world.structures[str(fire.id)] = fire
    for actor in (a, b):
        actor.needs.hunger = 25
        world.inventories[str(actor.id)].add("cooked_fish", 2)
        decisions._perception.observe(actor.id, 0)
    service.advance_all(1)
    assert a.metadata["community_task"]["kind"] == "meal"
    for tick in range(2, 6):
        for actor in (a, b):
            advance_routine(decisions, world, actor, tick, [])
    for actor in (a, b):
        assert world.inventories[str(actor.id)].items["cooked_fish"] == 1
        assert actor.needs.hunger == 3
        assert actor.metadata["last_community_task"]["status"] == "Shared meal completed"


def test_spoken_warning_keeps_expiry_and_records_provenance():
    world, a, b, _, service = community()
    a.metadata["wildlife_warning"] = {"x": 3, "y": 4, "expires": 10}
    service.advance_all(1)
    assert b.metadata["wildlife_warning"]["expires"] == 10
    assert "Danger near" in world.messages[0].content
    assert any(e.importance >= .8 for e in world.episodes[str(b.id)])
