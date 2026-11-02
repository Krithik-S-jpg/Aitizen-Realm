from tests.test_community_routines import community
from app.application.services.conversation_topics import discuss
from app.application.services.danger_memory import remember_attack
from app.domain.models.entity import Entity, EntityKind


def test_conversation_rotates_and_does_not_repeat_each_meeting():
    world, a, b, decisions, service = community()
    for tick in (1, 25, 49):
        discuss(service, world, a, b, tick)
    statements = [m.content for m in world.messages if m.sender_id == a.id]
    assert len(statements) == 3
    assert len(set(statements)) == 3


def test_attack_warning_retains_identity_and_source():
    world, a, b, decisions, service = community()
    b.x = 15
    b.y = 15
    wolf = Entity(kind=EntityKind.ANIMAL, name="Wolf", x=5, y=6,
                  metadata={"species": "wolf"})
    world.entities[str(wolf.id)] = wolf
    remember_attack(world, wolf, a, 1)
    b.x, b.y = 6, 5
    service.advance_all(30)
    assert any("attacked by a wolf" in m.content for m in world.messages)
    warning = b.metadata["wildlife_warning"]
    assert warning["attacker_id"] == str(wolf.id)
    assert warning["witness_id"] == str(a.id)
    assert warning["expires"] == 241
    assert world.episodes[str(b.id)][-2].importance >= .7 or any(e.importance >= .7 for e in world.episodes[str(b.id)])


def test_exploration_targets_unknown_boundary_not_known_world_corner():
    world, a, b, decisions, service = community()
    target = decisions._exploration_target(world, a)
    known = {(r.x, r.y) for r in world.entity_knowledge[str(a.id)].tiles.values()}
    x, y = target["x"], target["y"]
    assert (x, y) in known
    assert any((x+dx, y+dy) not in known for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))
               if 0 <= x+dx < world.width and 0 <= y+dy < world.height)


def test_frontier_walk_actually_expands_personal_knowledge():
    world, a, b, decisions, service = community()
    before = len(world.entity_knowledge[str(a.id)].tiles)
    target = decisions._exploration_target(world, a)
    decisions._navigation.plan(a.id, target["x"], target["y"], 1)
    for tick in range(2, 30):
        decisions._navigation.advance_all(tick)
        decisions._perception.observe(a.id, tick)
    assert len(world.entity_knowledge[str(a.id)].tiles) > before
