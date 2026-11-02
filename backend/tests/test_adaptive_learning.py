from app.application.services.adaptive_learning import (
    record_outcome, retry_blocked, update_ambition, danger_cost, safe_to_pursue,
)
from app.application.services.community_routines import converse
from app.application.services.danger_memory import remember_attack
from app.domain.models.cognition import Action, ActionType
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.world import World
from tests.test_community_routines import community
from uuid import uuid4


def test_actual_failure_cools_target_then_success_clears_it():
    world, a, _, _, _ = community()
    action = Action(entity_id=a.id, goal_id=uuid4(), action_type=ActionType.HUNT,
                    created_at_tick=0, target={"entity_id": "wolf"}, failure_reason="Escaped")
    record_outcome(a, action, 1, False)
    assert retry_blocked(a, "HUNT", action.target, 2)
    assert not retry_blocked(a, "HUNT", {"entity_id": "other"}, 2)
    assert not retry_blocked(a, "HUNT", action.target, 10)
    record_outcome(a, action, 10, True)
    assert not retry_blocked(a, "HUNT", action.target, 11)
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.entities[str(a.id)].metadata["action_lessons"] == a.metadata["action_lessons"]


def test_attack_warning_keeps_route_cost_after_save_and_fear_expiry():
    world, a, b, decisions, service = community()
    b.x, b.y = 19, 19
    wolf = Entity(kind=EntityKind.ANIMAL, name="Wolf", x=5, y=6, metadata={"species": "wolf"})
    world.entities[str(wolf.id)] = wolf
    remember_attack(world, wolf, a, 1)
    assert not b.metadata.get("learned_dangers")
    b.x, b.y = 7, 5
    assert converse(service, world, a, b, 30)
    restored = World.model_validate_json(world.model_dump_json())
    for actor_id in (a.id, b.id):
        actor = restored.entities[str(actor_id)]
        assert danger_cost(actor, 5, 5, 300) > danger_cost(actor, 15, 15, 300)
        assert danger_cost(actor, 5, 5, 1000) == 0
        assert next(iter(actor.metadata["learned_dangers"].values()))["observed_tick"] == 1


def test_ambition_is_stable_persisted_and_not_a_survival_override():
    world, a, _, _, _ = community()
    first = dict(update_ambition(world, a, 1))
    restored = World.model_validate_json(world.model_dump_json())
    actor = restored.entities[str(a.id)]
    assert update_ambition(restored, actor, 2) == first
    actor.needs.hunger = 90
    assert not safe_to_pursue(actor)


def test_learning_is_bounded():
    _, a, _, _, _ = community()
    for tick in range(60):
        action = Action(entity_id=a.id, goal_id=uuid4(), action_type=ActionType.MOVE,
                        created_at_tick=tick, target={"x": tick, "y": 0})
        record_outcome(a, action, tick, False)
    assert len(a.metadata["action_lessons"]) == 48


def test_learned_danger_changes_actual_path_after_reload():
    world, a, _, decisions, _ = community()
    # Fully observed empty terrain allows a genuine choice between safe routes.
    a.perception_radius = 12
    a.x, a.y = 1, 5
    decisions._perception.observe(a.id, 300)
    direct = decisions._navigation._find_path(world, a, 12, 5)
    a.metadata["learned_dangers"] = {"attack": {"x": 6, "y": 5, "observed_tick": 1}}
    a.metadata["decision_tick"] = 300
    restored = World.model_validate_json(world.model_dump_json())
    actor = restored.entities[str(a.id)]
    avoided = decisions._navigation._find_path(restored, actor, 12, 5)
    assert direct and avoided
    assert min((x-6)**2+(y-5)**2 for x,y in avoided) > min((x-6)**2+(y-5)**2 for x,y in direct)


def test_resource_tip_earns_trust_only_on_personal_confirmation():
    from app.application.services.adaptive_learning import verify_reports
    from app.domain.models.resource import ResourceNode, ResourceType
    world, a, b, decisions, service = community()
    resource = ResourceNode(resource_type=ResourceType.TREE, x=5, y=6, quantity=10, capacity=10)
    world.resources[str(resource.id)] = resource
    decisions._perception.observe(a.id, 1)
    service.send(a.id, b.id, "I saw a tree nearby.", 2, {"resources": [str(resource.id)]})
    bond = world.social_bonds[f"{b.id}:{a.id}"]
    before = bond.trust
    verify_reports(world, b, [], 3)
    assert bond.trust == before
    visible = [{"id": str(resource.id), "x": 5, "y": 6}]
    verify_reports(world, b, visible, 4)
    assert bond.trust == before + .05
    verify_reports(world, b, visible, 5)
    assert bond.trust == before + .05
