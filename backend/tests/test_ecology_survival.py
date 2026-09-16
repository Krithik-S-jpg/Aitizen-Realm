"""Regression tests for habitat travel and needs-driven settlement interactions."""

from uuid import UUID

from app.application.services.animal_service import AnimalService
from app.application.services.world_service import WorldService
from app.domain.models.cognition import ActionType, GoalType, TaskStatus
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import TerrainType
from tests.test_decisions import _systems


def test_ducks_do_not_spawn_in_dry_grassland() -> None:
    """The fallback species population pass must also enforce water habitat."""
    _, decisions, _ = _systems()
    world = decisions._require_world()  # noqa: SLF001
    WorldService._spawn_animals(world)  # noqa: SLF001
    assert not any(e.metadata.get("species") == "duck" for e in world.entities.values())


def test_wildlife_patrol_covers_ground_and_never_reports_zero_step() -> None:
    """Animals retain destinations instead of repeating a four-tile loop."""
    _, decisions, _ = _systems()
    world = decisions._require_world()  # noqa: SLF001
    deer = Entity(
        id=UUID(int=16),
        kind=EntityKind.ANIMAL,
        name="Deer",
        x=8,
        y=8,
        needs=NeedsState(),
        metadata={"species": "deer"},
    )
    service = AnimalService(decisions._repository)  # noqa: SLF001
    positions = set()
    for tick in range(20):
        service._patrol_habitat(world, deer, service.PROFILES["deer"], tick)  # noqa: SLF001
        positions.add((deer.x, deer.y))
    assert len(positions) >= 10
    assert not service._step_toward(world, deer, deer.x, deer.y, "patrol", 21)  # noqa: SLF001
    assert deer.metadata["state"] == "alert"


def test_full_pack_delivers_without_creating_resources() -> None:
    """An autonomous full carrier can unload into a nearby finished store."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Carrier", 5, 5, tags={"autonomous"})
    world = decisions._require_world()  # noqa: SLF001
    inventory = world.inventories[str(agent.id)]
    inventory.add("stone", 50)
    site = Structure(
        structure_type=StructureType.STORAGE,
        x=6,
        y=5,
        builder_id="test",
        work_required=1,
        progress=1,
    )
    world.structures[str(site.id)] = site
    _, action = decisions.decide(agent.id, 0)
    assert action.status == TaskStatus.COMPLETED
    assert action.result["transferred"] == 10
    assert inventory.items["stone"] + site.stockpile.items["stone"] == 50


def test_helper_completes_existing_site_without_paying_twice() -> None:
    """Construction recovery uses a real existing site's work and materials."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Helper", 5, 5, tags={"autonomous"})
    world = decisions._require_world()  # noqa: SLF001
    site = Structure(
        structure_type=StructureType.SHELTER,
        x=6,
        y=5,
        builder_id="departed",
        work_required=3,
        progress=1,
    )
    world.structures[str(site.id)] = site
    _, action = decisions.decide(agent.id, 0)
    decisions.advance_all(1)
    assert site.completed and action.status == TaskStatus.COMPLETED
    assert len(world.structures) == 1
    assert not world.inventories[str(agent.id)].items


def test_cold_agent_refuels_and_fire_consumes_fuel() -> None:
    """Fire warmth cannot persist without gathered, consumed wood."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Cold", 5, 5)
    assert agent.needs is not None
    agent.needs.body_temperature_c = 35.5
    world = decisions._require_world()  # noqa: SLF001
    world.inventories[str(agent.id)].add("wood", 4)
    site = Structure(
        structure_type=StructureType.CAMPFIRE,
        x=6,
        y=5,
        builder_id="test",
        work_required=1,
        progress=1,
    )
    world.structures[str(site.id)] = site
    _, action = decisions.decide(agent.id, 0)
    assert action.result["fuel_added"] == 4
    assert not world.inventories[str(agent.id)].items
    decisions._needs.advance_all(1)  # noqa: SLF001
    assert site.fuel == 3.75


def test_farm_grows_then_hungry_agent_harvests_real_food() -> None:
    """Harvest removes bounded produce from a completed farm after growth."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Farmer", 5, 5)
    world = decisions._require_world()  # noqa: SLF001
    site = Structure(
        structure_type=StructureType.FARM,
        x=6,
        y=5,
        builder_id="test",
        work_required=1,
        progress=1,
    )
    world.structures[str(site.id)] = site
    for tick in range(74):
        decisions._needs.advance_all(tick)  # noqa: SLF001
    assert site.crop_food == 12
    assert agent.needs is not None
    agent.needs.hunger = 80
    _, action = decisions.decide(agent.id, 74)
    assert action.result["harvested_food"] == 6
    assert site.crop_food == 6
    assert world.inventories[str(agent.id)].items["food"] == 6


def test_danger_preempts_work_and_warns_neighbour() -> None:
    """Only nearby citizens receive a time-limited wildlife warning."""
    entities, decisions, lifecycle = _systems()
    agent = entities.create(EntityKind.AGENT, "Scout", 5, 5, tags={"autonomous"})
    friend = entities.create(EntityKind.AGENT, "Friend", 5, 8, tags={"autonomous"})
    world = decisions._require_world()  # noqa: SLF001
    wolf = Entity(
        kind=EntityKind.ANIMAL, name="Wolf", x=7, y=5, metadata={"species": "wolf"}
    )
    world.entities[str(wolf.id)] = wolf
    decisions.advance_all(0)
    assert "wildlife_warning" in friend.metadata
    job = lifecycle.active(agent.id)
    assert job is not None and job[0].goal_type == GoalType.SEEK_SAFETY
    assert job[1].action_type == ActionType.MOVE
    assert (int(job[1].target["x"]) - wolf.x) ** 2 + (
        int(job[1].target["y"]) - wolf.y
    ) ** 2 > 4


def test_duck_population_is_always_close_to_water() -> None:
    """Wetland and river edges are required for duck spawning, even fallback."""
    _, decisions, _ = _systems()
    world = decisions._require_world()  # noqa: SLF001
    for x in range(16):
        tile = world.retrieve_tile(x, 8)
        assert tile is not None
        tile.terrain = TerrainType.WATER
        tile.walkable = False
    WorldService._spawn_animals(world)  # noqa: SLF001
    ducks = [e for e in world.entities.values() if e.metadata.get("species") == "duck"]
    assert ducks
    assert all(abs(e.y - 8) <= 3 for e in ducks)


def test_food_sharing_transfers_existing_inventory() -> None:
    """Sharing requires proximity and conserves both citizens' food."""
    entities, decisions, _ = _systems()
    donor = entities.create(EntityKind.AGENT, "Donor", 5, 5, tags={"autonomous"})
    receiver = entities.create(EntityKind.AGENT, "Hungry", 6, 5)
    assert receiver.needs is not None
    receiver.needs.hunger = 70
    world = decisions._require_world()  # noqa: SLF001
    world.inventories[str(donor.id)].add("fruit", 6)
    _, action = decisions.decide(donor.id, 0)
    decisions._navigation.advance_all(1)  # noqa: SLF001
    decisions.advance_all(1)
    assert action.status == TaskStatus.COMPLETED
    assert world.inventories[str(receiver.id)].items["fruit"] == 2
    assert world.inventories[str(donor.id)].items["fruit"] == 4


def test_warning_expires_without_being_rebroadcast_forever() -> None:
    """A rumour cannot renew itself when no citizen can see a predator."""
    entities, decisions, _ = _systems()
    agent = entities.create(EntityKind.AGENT, "Scout", 5, 5, tags={"autonomous"})
    agent.metadata["wildlife_warning"] = {"x": 7, "y": 5, "expires": 8}
    decisions.advance_all(2)
    assert agent.metadata["wildlife_warning"]["expires"] == 8
    agent.metadata["decision_tick"] = 9
    assert not decisions._threats(decisions._require_world(), agent)  # noqa: SLF001
