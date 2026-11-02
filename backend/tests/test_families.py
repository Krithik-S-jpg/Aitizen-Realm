import pytest
from app.application.services.family_service import advance, age_tick, stage
from app.domain.models.calendar import CalendarControl, configure_calendar_control, reset_calendar_control
from app.domain.models.entity import EntityKind
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World
from tests.test_decisions import _systems


@pytest.fixture(autouse=True)
def clock():
    reset_calendar_control()
    yield
    reset_calendar_control()


def test_age_separate_from_clock_and_duplicate_ticks():
    entities, _, _ = _systems()
    a = entities.create(EntityKind.AGENT,"Child",5,5)
    a.metadata.update(age_days=364, age_last_tick=0)
    configure_calendar_control(0,CalendarControl(ticks_per_day=1800, biological_days_per_day=1))
    age_tick(a,1800)
    assert stage(a)=="toddler"
    age_tick(a,1800)
    assert a.metadata["age_days"]==365
    configure_calendar_control(1800,CalendarControl(biological_days_per_day=0))
    age_tick(a,3600)
    assert a.metadata["age_days"]==365


def test_birth_once_after_reload_and_care_uses_real_food():
    entities, decisions, _ = _systems()
    world=decisions._require_world()
    mother=entities.create(EntityKind.AGENT,"Mother",5,5,gender="female")
    father=entities.create(EntityKind.AGENT,"Father",6,5,gender="male")
    mother.metadata.update(age_days=25*365, pregnancy={"id":"test-birth","partner_id":str(father.id),"due_age_days":25*365})
    home=Structure(structure_type=StructureType.SHELTER,x=5,y=5,builder_id=str(mother.id),progress=1,work_required=1,bed_capacity=3,resident_ids=[str(mother.id),str(father.id)])
    world.structures[str(home.id)]=home
    advance(world,1)
    restored=World.model_validate_json(world.model_dump_json())
    advance(restored,1)
    advance(restored,2)
    babies=[a for a in restored.entities.values() if a.metadata.get("birth_tick")==1]
    assert len(babies)==1
    baby=babies[0]
    assert baby.metadata["parent_ids"]==[str(mother.id),str(father.id)]
    baby.needs.hunger=50
    for p in (mother,father):
        restored.inventories[str(p.id)].add("food",2)
    before=sum(i.items.get("food",0) for i in restored.inventories.values())
    advance(restored,3)
    assert baby.needs.hunger==30
    assert sum(i.items.get("food",0) for i in restored.inventories.values())==before-1


def test_minor_cannot_decide_dive_or_hunt():
    from app.application.services.hunting import target
    from app.application.services.group_expeditions import ready
    entities,decisions,_=_systems()
    a=entities.create(EntityKind.AGENT,"Young",5,5,tags={"autonomous"})
    a.metadata["age_days"]=5*365
    with pytest.raises(ValueError,match="Minors"):
        decisions.decide(a.id,1)
    with pytest.raises(ValueError,match="adults"):
        decisions._navigation.explore_underwater(a.id,1)
    with pytest.raises(ValueError,match="adults"):
        target(decisions,decisions._require_world(),a)
    assert not ready(decisions._require_world(),a,1)
