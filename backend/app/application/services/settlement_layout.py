"""Derived, non-destructive settlement courts and walkable doorway paths."""
from collections import deque
from app.application.services.terrain_elevation import can_step, level


def refresh(world):
    tiles = {(t.x,t.y):t for c in world.chunks.values() for t in c.tiles.values()}
    for tile in tiles.values():
        tile.metadata.pop('settlement_path',None)
        tile.metadata.pop('settlement_square',None)
    sites = [s for s in world.structures.values() if s.completed]
    blocked = {p for s in sites if s.structure_type.value not in {'ROAD','BRIDGE','CAMPFIRE','TORCH'} for p in s.footprint}
    blocked |= {(r.x,r.y) for r in world.resources.values() if not r.depleted and r.resource_type.value in {'TREE','STONE','ORE'}}
    anchors = sorted([s for s in sites if s.structure_type.value in {'WELL','CAMPFIRE'}],key=lambda s:str(s.id))
    for anchor in anchors:
        origin = (anchor.x,anchor.y)
        center = tiles.get(origin)
        if not center:
            continue
        court = set()
        for dx in range(-1,2):
            for dy in range(-1,2):
                p = (anchor.x+dx,anchor.y+dy)
                tile = tiles.get(p)
                if tile and tile.walkable and p not in blocked and level(tile)==level(center) and not tile.metadata.get('ramps'):
                    tile.metadata['settlement_square'] = True
                    court.add(p)
        if not court:
            continue
        for home in sites:
            if home.structure_type.value not in {'SHELTER','TENT','STORAGE','WORKBENCH','FARM'}:
                continue
            start = home.entrance
            if abs(start[0]-anchor.x)+abs(start[1]-anchor.y)>16:
                continue
            queue, parents = deque([start]), {start:None}
            end = None
            while queue and len(parents)<512:
                p = queue.popleft()
                if p in court:
                    end = p
                    break
                for q in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
                    tile = tiles.get(q)
                    if q not in parents and q not in blocked and tile and tile.walkable and can_step(world,p,q):
                        parents[q] = p
                        queue.append(q)
            while end is not None:
                tiles[end].metadata['settlement_path'] = True
                end = parents[end]
