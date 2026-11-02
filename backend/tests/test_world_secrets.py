from app.application.services.world_secrets import initialize, observe, journal, target
from app.application.services.world_generator import WorldGenerator
from app.domain.models.world import World
from tests.test_community_routines import community


def test_seeded_history_is_stable_and_different_between_worlds():
    worlds = [WorldGenerator.generate_flat_world(16, 16) for _ in range(3)]
    for w, seed in zip(worlds, [71, 71, 72]):
        w.seed = seed
        initialize(w)
    assert worlds[0].ancient_sites == worlds[1].ancient_sites
    assert worlds[0].ancient_sites != worlds[2].ancient_sites
    assert len(worlds[0].ancient_sites) == 3
    assert not journal(worlds[0])
    assert World.model_validate_json(worlds[0].model_dump_json()).ancient_sites == worlds[0].ancient_sites


def setup_mystery():
    world, a, b, decisions, communication = community()
    world.seed = 71
    initialize(world)
    return world, a, b, decisions, communication


def test_sighting_does_not_reveal_clue_until_physical_inspection():
    world, a, b, decisions, chat = setup_mystery()
    site = next(iter(world.ancient_sites.values()))
    a.x, a.y = site["x"]-2, site["y"]
    observe(world, a, 1)
    record = world.entity_knowledge[str(a.id)].discoveries[site["id"]]
    assert "evidence" not in record.data
    a.x, a.y = site["x"], site["y"]
    decisions._perception.observe(a.id, 2)
    assert world.entity_knowledge[str(a.id)].discoveries[site["id"]].data["inspected"]
    count = len(world.episodes[str(a.id)])
    observe(world, a, 3)
    assert len(world.episodes[str(a.id)]) == count
    entry = next(e for e in journal(world) if e["id"] == site["id"])
    assert entry["evidence"] == site["evidence"]
    assert entry["discoverers"][0]["tick"] == 1
    assert not world.inventories[str(a.id)].items  # Artifacts examined, not conjured into packs.


def test_shared_clue_is_hearsay_and_route_stays_in_known_tiles():
    world, a, b, decisions, chat = setup_mystery()
    site = next(iter(world.ancient_sites.values()))
    a.x, a.y = site["x"], site["y"]
    decisions._perception.observe(a.id, 1)
    b.x, b.y = (a.x+2 if a.x+2 < world.width else a.x-2), a.y
    decisions._perception.observe(b.id, 1)
    chat.send(a.id, b.id, "Here is the inscription I read.", 2, {"discoveries": [site["id"]]})
    learned = world.entity_knowledge[str(b.id)].discoveries[site["id"]]
    assert learned.confidence == .75 and learned.source_entity_id == a.id
    route = target(world, b)
    assert f"{route['x']},{route['y']}" in world.entity_knowledge[str(b.id)].tiles
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.entity_knowledge[str(b.id)].discoveries[site["id"]].source_entity_id == a.id


def test_llm_context_does_not_leak_undiscovered_history():
    from app.application.services.citizen_dialogue import context_for
    world, a, b, decisions, chat = setup_mystery()
    context = context_for(world, a, b)
    assert context["archaeological_evidence"] == []


def test_citizen_follows_a_real_clue_trail_without_map_reveal():
    world, a, b, decisions, chat = setup_mystery()
    sites = list(world.ancient_sites.values())
    a.x, a.y = sites[0]["x"], sites[0]["y"]
    for tick in range(1, 65):
        decisions._perception.observe(a.id, tick)
        route = target(world, a)
        if route is None:
            break
        before = len(world.entity_knowledge[str(a.id)].tiles)
        decisions._navigation.plan(a.id, route["x"], route["y"], tick)
        assert len(world.entity_knowledge[str(a.id)].tiles) == before
        x, y = a.x, a.y
        decisions._navigation.advance_all(tick)
        assert abs(a.x-x)+abs(a.y-y) <= 1
    assert all(str(a.id) in s["inspected_by"] for s in sites)


def test_generated_interpretation_does_not_rewrite_evidence():
    world, a, b, decisions, chat = setup_mystery()
    site = next(iter(world.ancient_sites.values()))
    a.x, a.y = site["x"], site["y"]
    b.x, b.y = a.x, a.y
    decisions._perception.observe(a.id, 1)
    fact = site["evidence"]
    chat.send(a.id, b.id, "Perhaps this tower was built by dragons.", 2,
              {"discoveries": [site["id"]]}, origin="local_llm")
    assert site["evidence"] == fact
    assert world.entity_knowledge[str(b.id)].discoveries[site["id"]].data["evidence"] == fact
    assert site["interpretations"][0]["status"] == "Citizen interpretation, not verified history"
