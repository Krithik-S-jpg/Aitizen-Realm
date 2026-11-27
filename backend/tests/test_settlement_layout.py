import pytest
from app.application.services.world_generator import WorldGenerator
from app.application.services.settlement_layout import refresh
from app.application.services.construction_service import ConstructionService
from app.domain.models.structure import Structure, StructureType


def test_court_and_paths_preserve_world_and_reserve_open_space():
    world = WorldGenerator.generate_flat_world(16,16)
    world.resources.clear()
    for kind,x,y in [(StructureType.CAMPFIRE,8,8),(StructureType.SHELTER,4,8)]:
        site = Structure(structure_type=kind,x=x,y=y,builder_id='test',work_required=1,footprint_version=2)
        site.apply_work(1)
        world.structures[str(site.id)] = site
    refresh(world)
    assert world.retrieve_tile(8,8).metadata['settlement_square']
    assert world.retrieve_tile(5,8).metadata['settlement_path']
    assert len(world.structures)==2
    with pytest.raises(ValueError,match='square'):
        ConstructionService.validate_space(world,StructureType.STORAGE,8,8)
    before = world.model_dump_json()
    refresh(world)
    assert world.model_dump_json()==before
