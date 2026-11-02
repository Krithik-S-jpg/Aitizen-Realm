import pytest
from app.domain.models.world import World
from tests.test_water_travel import crossing


def test_dive_explores_known_water_and_returns_with_oxygen():
    world, citizen, navigation, _ = crossing(width=3)
    plan = navigation.explore_underwater(citizen.id, 0)
    assert len(plan.path) <= 7
    navigation.advance_all(1)
    assert citizen.metadata["underwater"]
    assert citizen.metadata["oxygen"] == 88
    with pytest.raises(ValueError):
        navigation.cancel(citizen.id)
    with pytest.raises(ValueError):
        navigation.plan(citizen.id, 3, 6, 1)
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.entities[str(citizen.id)].metadata["oxygen"] == 88
    for tick in range(2, len(plan.path)):
        navigation.advance_all(tick)
    assert (citizen.x, citizen.y) == (3, 5)
    assert not citizen.metadata["underwater"]
    assert not citizen.metadata["dive_trip"]
    assert citizen.metadata["underwater_explored"]
    assert citizen.needs.energy > 0


def test_dive_rejects_tired_citizens_and_deep_water():
    _, citizen, navigation, _ = crossing()
    citizen.needs.energy = 60
    with pytest.raises(ValueError):
        navigation.explore_underwater(citizen.id, 0)
    _, citizen, navigation, _ = crossing(ocean=True)
    with pytest.raises(ValueError):
        navigation.explore_underwater(citizen.id, 0)


def test_recall_retraces_visited_tiles_and_preserves_tick_guard():
    world, citizen, navigation, _ = crossing(width=3)
    navigation.explore_underwater(citizen.id, 0)
    navigation.advance_all(1)
    position = (citizen.x, citizen.y)
    plan = navigation.return_from_dive(citizen.id, 1)
    assert plan.path == [position, (3, 5)]
    navigation.advance_all(1)
    assert (citizen.x, citizen.y) == position
    navigation.advance_all(2)
    assert (citizen.x, citizen.y) == (3, 5)
    assert not citizen.metadata["dive_trip"]
    assert not citizen.metadata["underwater"]


def test_low_reserve_turns_diver_back_before_exhaustion():
    _, citizen, navigation, _ = crossing(width=3)
    navigation.explore_underwater(citizen.id, 0)
    navigation.advance_all(1)
    citizen.needs.energy = 35
    navigation.advance_all(2)
    assert (citizen.x, citizen.y) == (3, 5)
    assert citizen.needs.energy > 0
    assert not citizen.metadata["dive_trip"]
