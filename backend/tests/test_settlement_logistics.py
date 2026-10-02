"""Material logistics, finite housing, and observable settlement jobs."""

import pytest

from app.application.services.construction_service import ConstructionService
from app.application.services.settlement_service import SettlementService
from app.application.services.society_service import SocietyService
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from tests.test_decisions import _systems


def test_construction_requires_visible_delivery_before_work() -> None:
    """Two citizens fund one site in trips before construction can advance."""
    entities, decisions, _ = _systems()
    world = decisions._repository.get()
    builder = entities.create(EntityKind.AGENT, "Builder", 5, 5)
    hauler = entities.create(EntityKind.AGENT, "Hauler", 6, 6)
    construction = ConstructionService(decisions._repository)

    site = construction.start_site(str(builder.id), StructureType.CAMPFIRE, x=6, y=5)
    assert site.missing_materials == {"wood": 5.0, "stone": 8.0}
    with pytest.raises(ValueError, match="waiting for delivered materials"):
        construction.apply_work(site.id, str(builder.id), 1.0)

    world.inventories[str(builder.id)].add("wood", 5.0)
    world.inventories[str(hauler.id)].add("stone", 8.0)
    assert construction.deliver_materials(site.id, str(builder.id)) == {"wood": 5.0}
    assert site.missing_materials == {"stone": 8.0}
    assert construction.deliver_materials(site.id, str(hauler.id)) == {"stone": 8.0}
    assert site.funded
    assert world.inventories[str(builder.id)].items == {}
    assert world.inventories[str(hauler.id)].items == {}

    construction.apply_work(site.id, str(builder.id), site.work_required)
    assert site.completed


def test_households_respect_beds_and_expand_into_a_second_home() -> None:
    """Residents receive stable, unique beds without exceeding occupancy."""
    entities, decisions, _ = _systems()
    world = decisions._repository.get()
    citizens = [
        entities.create(EntityKind.AGENT, f"Citizen {index}", 4 + index, 5)
        for index in range(5)
    ]
    society = SocietyService(decisions._repository)
    settlement = SettlementService(decisions._repository)
    society.advance_all(0)
    assert len(world.groups) == 1

    shelter = Structure(
        structure_type=StructureType.SHELTER,
        x=5,
        y=6,
        builder_id=str(citizens[0].id),
        work_required=35,
        progress=35,
        bed_capacity=4,
    )
    world.structures[str(shelter.id)] = shelter
    settlement.advance_all(1)
    assigned = [citizen for citizen in citizens if not citizen.metadata["homeless"]]
    assert len(assigned) == 4
    assert len(shelter.resident_ids) == 4
    assert len({citizen.metadata["bed_index"] for citizen in assigned}) == 4

    tent = Structure(
        structure_type=StructureType.TENT,
        x=6,
        y=6,
        builder_id=str(citizens[1].id),
        work_required=18,
        progress=18,
        bed_capacity=2,
    )
    world.structures[str(tent.id)] = tent
    settlement.advance_all(2)
    assert all(not citizen.metadata["homeless"] for citizen in citizens)
    assert sum(len(home.resident_ids) for home in (shelter, tent)) == 5
    assert len(world.households) == 2


def test_job_board_reports_material_shortages_and_funded_work() -> None:
    """Settlement jobs change from delivery requests to funded construction."""
    entities, decisions, _ = _systems()
    world = decisions._repository.get()
    citizen = entities.create(EntityKind.AGENT, "Citizen", 5, 5)
    entities.create(EntityKind.AGENT, "Helper", 5, 6)
    SocietyService(decisions._repository).advance_all(0)
    construction = ConstructionService(decisions._repository)
    settlement = SettlementService(decisions._repository)
    site = construction.start_site(str(citizen.id), StructureType.CAMPFIRE, x=6, y=5)

    settlement.advance_all(1)
    open_jobs = [job for job in world.settlement_jobs.values() if job.status == "open"]
    assert {job.material for job in open_jobs} == {"wood", "stone"}
    assert all(job.job_type == "deliver_construction" for job in open_jobs)

    world.inventories[str(citizen.id)].add("wood", 5)
    world.inventories[str(citizen.id)].add("stone", 8)
    construction.deliver_materials(site.id, str(citizen.id))
    settlement.advance_all(2)
    open_jobs = [job for job in world.settlement_jobs.values() if job.status == "open"]
    assert len(open_jobs) == 1
    assert open_jobs[0].job_type == "build"
