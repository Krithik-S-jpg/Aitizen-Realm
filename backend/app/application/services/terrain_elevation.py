"""Versioned terrace geometry. Missing metadata means a legacy flat world."""

WATER = {"WATER", "OCEAN"}


def level(tile):
    return int(tile.metadata.get("bridge_level", tile.metadata.get("terrace", 0))) if tile else 0


def can_step(world, start, end):
    a, b = world.retrieve_tile(*start), world.retrieve_tile(*end)
    if not a or not b:
        return False
    if level(a) == level(b):
        return True
    if abs(start[0]-end[0])+abs(start[1]-end[1]) != 1:
        return False
    return abs(level(a)-level(b)) == 1 and (
        list(end) in a.metadata.get("ramps", []) or list(start) in b.metadata.get("ramps", []))


def initialize(world):
    """Initialize generated terrain, preserving already initialized cells."""
    world.elevation_version = 1
    tiles = {(t.x,t.y):t for c in world.chunks.values() for t in c.tiles.values()}
    fresh = {p for p,t in tiles.items() if "terrace" not in t.metadata}
    for tile in tiles.values():
        # Broad connected landforms rather than isolated one-cell pillars.
        elevation = float(tile.metadata.get("elevation",.3))
        neighbors = [float(tiles[(tile.x+dx,tile.y+dy)].metadata.get("elevation",.3))
                     for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))
                     if (tile.x+dx,tile.y+dy) in tiles]
        smooth = elevation*.65 + (sum(neighbors)/len(neighbors) if neighbors else elevation)*.35
        height = max(0,min(4,int((smooth-.3)*8)))
        if tile.terrain.value in WATER:
            height = max(0,height-1) if tile.metadata.get("river") else 0
        tile.metadata.setdefault("terrace",height)
        tile.metadata.setdefault("elevation_version",1)
        tile.metadata.setdefault("ramps",[])
    # The river's stored flow direction guarantees no upstream step in water.
    for _ in range(len(tiles)):
        changed = False
        for tile in tiles.values():
            dest = tiles.get(tuple(tile.metadata.get("flow_to", [])))
            if dest and (dest.x,dest.y) in fresh and level(dest) > level(tile):
                dest.metadata["terrace"] = level(tile)
                changed = True
        if not changed:
            break
    # Connect equal-height land into regions, then add bounded stair edges
    # between neighboring terraces. This preserves routes without making every
    # cliff climbable. No resource or citizen is moved.
    parent = {p:p for p,t in tiles.items() if t.walkable}
    def root(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    edges = []
    for p in sorted(parent):
        for q in ((p[0]+1,p[1]),(p[0],p[1]+1)):
            if q not in parent:
                continue
            delta = abs(level(tiles[p])-level(tiles[q]))
            if delta == 0:
                parent[root(p)] = root(q)
            elif delta == 1 and (list(q) in tiles[p].metadata["ramps"] or list(p) in tiles[q].metadata["ramps"]):
                parent[root(p)] = root(q)
            elif delta == 1 and p in fresh and q in fresh:
                edges.append((p,q))
    for p,q in edges:
        if root(p) != root(q) or (p[0]*13+p[1]*7)%11 == 0:
            if list(q) not in tiles[p].metadata["ramps"]:
                tiles[p].metadata["ramps"].append(list(q))
            if list(p) not in tiles[q].metadata["ramps"]:
                tiles[q].metadata["ramps"].append(list(p))
            parent[root(p)] = root(q)
    # Generated stairs must not spawn underneath a tree or mineral node.
    world.resources = {key:r for key,r in world.resources.items()
                       if (r.x,r.y) not in fresh or not tiles[(r.x,r.y)].metadata.get("ramps")}
