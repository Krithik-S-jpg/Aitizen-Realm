from concurrent.futures import Future
from tests.test_citizen_chat import setup_chat
from app.application.services.citizen_dialogue import CitizenDialogue, context_for


def completed(world, a, b, value):
    engine = CitizenDialogue()
    engine.pending = Future()
    engine.pending.set_result(value)
    engine.context = (world, str(a.id), str(b.id), 1)
    return engine


def test_generated_exchange_is_delivered_without_actions_or_inventory_changes():
    world, a, b, service = setup_chat()
    engine = completed(world, a, b, ["What would you like to discover?", "I'd like to learn where the river leads."])
    before = {key: inv.model_dump() for key, inv in world.inventories.items()}
    engine.advance(service, world, 2)
    assert len(world.messages) == 2
    assert a.metadata["conversation"][0]["origin"] == "local_llm"
    assert before == {key: inv.model_dump() for key, inv in world.inventories.items()}
    assert not world.actions


def test_departed_partner_and_changed_world_discard_dialogue():
    world, a, b, service = setup_chat()
    engine = completed(world, a, b, ["Hello", "Hello"])
    b.x = 15
    engine.advance(service, world, 2)
    assert not world.messages
    engine = completed(object(), a, b, ["Hello", "Hello"])
    engine.advance(service, world, 2)
    assert not world.messages


def test_invalid_output_is_not_published():
    world, a, b, service = setup_chat()
    engine = completed(world, a, b, ["Hello", "x" * 241])
    engine.advance(service, world, 2)
    assert not world.messages
    assert "unavailable" in a.metadata["dialogue_status"]


def test_context_does_not_include_partners_private_information():
    world, a, b, service = setup_chat()
    b.metadata["last_decision_reason"] = "PRIVATE PARTNER PLAN"
    assert "PRIVATE PARTNER PLAN" not in str(context_for(world, a, b))
