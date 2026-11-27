import pytest
from app.application.services.terrain_elevation import initialize, level, can_step
from app.application.services.world_generator import WorldGenerator
from app.application.services.construction_service import ConstructionService
from app.domain.models.structure import StructureType
from app.domain.models.world import World
from tests.test_water_travel import crossing


def test_legacy_world_stays_flat_after_reload():
    world = WorldGenerator.generate_flat_world(12,12)
    world.retrieve_tile(4,4).metadata['elevation'] = .95
    restored = World.model_validate_json(world.model_dump_json())
    assert restored.elevation_version == 0
    assert level(restored.retrieve_tile(4,4)) == 0


def test_cliff_is_blocked_until_marked_stair_and_survives_save():
    world, actor, nav, decisions = crossing()
    actor.x,actor.y = 3,5
    world.resources.clear()
    from app.domain.models.world import TerrainType
    for chunk in world.chunks.values():
        for tile in chunk.tiles.values():
            tile.terrain = TerrainType.GRASS
            tile.walkable = True
            tile.metadata['terrace'] = int(tile.x >= 4)
    decisions._perception.observe(actor.id,1)
    assert not can_step(world,(3,5),(4,5))
    with pytest.raises(ValueError):
        nav.plan(actor.id,4,5,1)
    world.retrieve_tile(3,5).metadata['ramps'] = [[4,5]]
    plan = nav.plan(actor.id,4,5,2)
    assert plan.path[-1] == (4,5)
    restored = World.model_validate_json(world.model_dump_json())
    assert can_step(restored,(4,5),(3,5))
    assert not can_step(restored,(3,4),(4,5))
    world.retrieve_tile(3,5).metadata['ramps'] = []
    nav.advance_all(3)
    assert (actor.x,actor.y) == (3,5)


def test_foundation_cannot_span_cliff():
    world,actor,nav,decisions = crossing()
    world.resources.clear()
    world.retrieve_tile(9,9).metadata['terrace']=1
    with pytest.raises(ValueError,match='level terrace'):
        ConstructionService.validate_space(world,StructureType.SHELTER,9,9)


def test_new_world_levels_are_deterministic_and_ramps_clear():
    a = WorldGenerator.generate_terrain_world(32,32,847291)
    b = WorldGenerator.generate_terrain_world(32,32,847291)
    assert a.elevation_version == 1
    assert [t.metadata.get('terrace') for c in a.chunks.values() for t in c.tiles.values()] == [t.metadata.get('terrace') for c in b.chunks.values() for t in c.tiles.values()]
    assert any(level(t)>0 for c in a.chunks.values() for t in c.tiles.values())
    for c in a.chunks.values():
        for t in c.tiles.values():
            for end in t.metadata.get('ramps',[]):
                assert can_step(a,(t.x,t.y),tuple(end))
                assert not a.resources_at(t.x,t.y)
            if t.metadata.get('flow_to'):
                assert level(a.retrieve_tile(*t.metadata['flow_to'])) <= level(t)


def test_bridge_deck_matches_banks_and_rejects_uneven_crossing():
    world,actor,nav,decisions = crossing(width=1)
    world.resources.clear()
    service = ConstructionService(decisions._repository)
    world.retrieve_tile(3,5).metadata['terrace'] = 2
    world.retrieve_tile(5,5).metadata['terrace'] = 1
    with pytest.raises(ValueError,match='matching elevations'):
        service.start_site(str(actor.id),StructureType.BRIDGE,4,5)
    world.retrieve_tile(5,5).metadata['terrace'] = 2
    site = service.start_site(str(actor.id),StructureType.BRIDGE,4,5)
    site.materials_delivered = site.materials_required.copy()
    service.apply_work(site.id,str(actor.id),site.work_required)
    assert world.retrieve_tile(4,5).metadata['bridge_level'] == 2
    assert can_step(world,(3,5),(4,5))
    assert can_step(world,(4,5),(5,5))


def test_initializing_existing_cells_preserves_resources_and_stairs():
    world = WorldGenerator.generate_terrain_world(32,32,847291)
    before = world.model_dump_json()
    initialize(world)
    assert world.model_dump_json() == before


def test_legacy_upgrade_preserves_content_and_walkable_edges():
    from app.application.services.terrain_elevation import upgrade_legacy
    from app.domain.models.structure import Structure
    world = WorldGenerator.generate_flat_world(16,16)
    for chunk in world.chunks.values():
        for tile in chunk.tiles.values():
            tile.metadata['elevation'] = .55 + tile.x*.02
    site = Structure(structure_type=StructureType.SHELTER,x=8,y=8,footprint_version=2,builder_id="test",work_required=10)
    world.structures[str(site.id)] = site
    contents = (world.resources.copy(),world.entities.copy(),world.structures.copy())
    original = world.model_dump_json()
    assert upgrade_legacy(world)
    assert contents == (world.resources,world.entities,world.structures)
    assert len({level(world.retrieve_tile(*p)) for p in site.footprint | {site.entrance}}) == 1
    for chunk in world.chunks.values():
        for tile in chunk.tiles.values():
            for q in ((tile.x+1,tile.y),(tile.x,tile.y+1)):
                if world.retrieve_tile(*q):
                    assert can_step(world,(tile.x,tile.y),q)
    upgraded = world.model_dump_json()
    assert not upgrade_legacy(world)
    assert world.model_dump_json() == upgraded
    assert World.model_validate_json(original).elevation_version == 0
