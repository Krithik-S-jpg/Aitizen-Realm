"""Attacks have physical range, shelter protection and personal consequences."""

from app.application.services.animal_service import AnimalService
from app.application.services.danger_memory import fear_at, sheltered
from app.application.services.entity_presentation import activity_details
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_decisions import _systems


def test_attack_witnesses_cooldown_and_persistent_memory():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    victim = entities.create(EntityKind.AGENT, "Victim", 5, 5)
    witness = entities.create(EntityKind.AGENT, "Witness", 7, 5)
    distant = entities.create(EntityKind.AGENT, "Distant", 15, 15)
    sleeper = entities.create(EntityKind.AGENT, "Sleeper", 6, 6)
    sleeper.metadata["state"] = "sleep"
    wolf = entities.create(EntityKind.ANIMAL, "Wolf", 4, 5)
    wolf.metadata["species"] = "wolf"
    from app.domain.models.needs import NeedsState
    wolf.needs = NeedsState(hunger=80)
    service = AnimalService(decisions._repository)
    before = victim.needs.health
    assert service._attack_citizen(world, wolf, 10)
    assert victim.needs.health == before - 12
    assert not service._attack_citizen(world, wolf, 11)
    assert victim.needs.health == before - 12
    assert world.episodes[str(victim.id)][-1].details["experience"] == "attacked"
    assert world.episodes[str(witness.id)][-1].details["experience"] == "witnessed"
    assert not world.episodes[str(distant.id)]
    assert not world.episodes[str(sleeper.id)]
    assert fear_at(witness, 10) == 45
    assert fear_at(witness, 100) == 0
    assert decisions._threats(world, witness)
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.episodes[str(witness.id)][-1].details["attacker_id"] == str(wolf.id)


def test_valid_shelter_hides_and_protects_sleeping_resident():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    resident = entities.create(EntityKind.AGENT, "Resident", 5, 5)
    home = Structure(structure_type=StructureType.TENT, x=5, y=6, builder_id=str(resident.id),
                     work_required=1, progress=1, bed_capacity=2, resident_ids=[str(resident.id)])
    world.structures[str(home.id)] = home
    resident.metadata.update(state="sleep", indoors=True, sleep_home_id=str(home.id))
    assert sheltered(world, resident)
    assert activity_details(world, resident)["indoors"]
    assert decisions._threats(world, resident) == []
    bear = entities.create(EntityKind.ANIMAL, "Bear", 4, 5)
    bear.metadata["species"] = "bear"
    assert not AnimalService(decisions._repository)._attack_citizen(world, bear, 4)
    home.progress = 0
    assert not activity_details(world, resident)["indoors"]


def test_distant_wolf_cannot_damage_without_reaching_target():
    entities, decisions, _ = _systems()
    world = decisions._require_world()
    target = entities.create(EntityKind.AGENT, "Citizen", 8, 5)
    wolf = entities.create(EntityKind.ANIMAL, "Wolf", 5, 5)
    wolf.metadata["species"] = "wolf"
    from app.domain.models.needs import NeedsState
    wolf.needs = NeedsState(hunger=80)
    AnimalService(decisions._repository)._attack_citizen(world, wolf, 1)
    assert target.needs.health == 100
    assert not world.episodes[str(target.id)]
