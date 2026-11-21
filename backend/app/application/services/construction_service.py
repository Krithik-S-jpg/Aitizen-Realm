"""Blueprint placement, material consumption, and construction work."""

from math import isfinite
from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.resource import ResourceType
from app.domain.models.structure import Structure, StructureType
from app.domain.models.world import World


class ConstructionService:
    """Owns the lifecycle of backend-authoritative structures."""

    BLUEPRINTS: dict[StructureType, tuple[dict[str, float], float]] = {
        StructureType.CAMPFIRE: ({"wood": 5.0, "stone": 8.0}, 12.0),
        StructureType.SHELTER: ({"wood": 20.0, "stone": 5.0}, 35.0),
        StructureType.STORAGE: ({"wood": 12.0, "stone": 8.0}, 24.0),
        StructureType.TENT: ({"wood": 8.0, "fiber": 12.0}, 18.0),
        StructureType.WORKBENCH: ({"wood": 14.0, "stone": 4.0}, 22.0),
        StructureType.WELL: ({"stone": 24.0, "wood": 6.0}, 38.0),
        StructureType.TORCH: ({"wood": 3.0, "fiber": 2.0}, 6.0),
        StructureType.FENCE: ({"wood": 5.0}, 8.0),
        StructureType.FARM: ({"wood": 6.0, "fiber": 4.0}, 24.0),
        StructureType.ROAD: ({"stone": 2.0}, 6.0),
        StructureType.BRIDGE: ({"wood": 16.0, "stone": 4.0}, 28.0),
    }
    PROGRESSION = (
        StructureType.SHELTER,
        StructureType.CAMPFIRE,
        StructureType.WORKBENCH,
        StructureType.STORAGE,
        StructureType.WELL,
        StructureType.FENCE,
    )

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes construction against the shared world repository."""
        self._repository = repository

    def place(
        self, actor_id: str, structure_type: StructureType, x: int, y: int
    ) -> Structure:
        """Consumes a recipe and places an unfinished structure site."""
        world = self._require_world()
        structure = self.start_site(actor_id, structure_type, x, y)
        inventory = world.inventories.get(actor_id)
        if inventory is None:
            world.structures.pop(str(structure.id), None)
            raise ValueError("Actor has no inventory.")
        requirements = structure.materials_required
        try:
            inventory.consume(requirements)
        except ValueError:
            world.structures.pop(str(structure.id), None)
            raise
        structure.materials_delivered = requirements.copy()
        return structure

    @classmethod
    def validate_space(cls, world, kind, x, y):
        """Validate every foundation cell and preserve an accessible doorstep."""
        if kind == StructureType.BRIDGE:
            return
        probe = Structure(structure_type=kind, x=x, y=y, builder_id="",
                          work_required=1, footprint_version=2)
        footprint = probe.footprint
        large = len(footprint) > 1
        reserved = footprint | ({probe.entrance} if kind not in {
            StructureType.ROAD, StructureType.FARM, StructureType.CAMPFIRE, StructureType.TORCH} else set())
        solid = {(r.x, r.y) for r in world.resources.values() if not r.depleted
                 and r.resource_type in {ResourceType.TREE, ResourceType.STONE, ResourceType.ORE}}
        for point in reserved:
            tile = world.retrieve_tile(*point)
            if not tile or not tile.walkable or tile.metadata.get("cave"):
                raise ValueError("Foundation and entrance require clear, loaded land.")
            if point in solid:
                raise ValueError("Clear trees and rocks from the foundation and entrance.")
        if any(not resource.depleted and (resource.x, resource.y) in footprint for resource in world.resources.values()):
            raise ValueError("Clear resources from the foundation first.")
        if any(entity.active and (entity.x, entity.y) in footprint for entity in world.entities.values()):
            raise ValueError("Wait for citizens and animals to leave the foundation.")
        for existing in world.structures.values():
            if reserved & existing.footprint or (existing.footprint_version >= 2 and existing.entrance in footprint):
                raise ValueError("Foundation overlaps a building or its entrance.")
            if (large or len(existing.footprint) > 1) and kind not in {StructureType.ROAD, StructureType.BRIDGE, StructureType.TORCH} and existing.structure_type not in {StructureType.ROAD, StructureType.BRIDGE, StructureType.TORCH} and any(
                abs(a[0]-b[0])+abs(a[1]-b[1]) <= 1 for a in footprint for b in existing.footprint
            ):
                raise ValueError("Leave a walking lane between large buildings.")

    def start_site(
        self, actor_id: str, structure_type: StructureType, x: int, y: int
    ) -> Structure:
        """Places an unfunded foundation so supplies can arrive over several trips."""
        world = self._require_world()
        tile = world.retrieve_tile(x, y)
        if tile is None:
            raise LookupError("Construction tile is not loaded.")
        if structure_type == StructureType.BRIDGE:
            from app.domain.models.world import TerrainType
            banks = [world.retrieve_tile(x + dx, y + dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
            dry = [b is not None and b.walkable and b.terrain not in {TerrainType.WATER, TerrainType.OCEAN} for b in banks]
            if tile.terrain != TerrainType.WATER or not ((dry[0] and dry[1]) or (dry[2] and dry[3])):
                raise ValueError("A bridge requires a narrow freshwater crossing with opposite dry banks.")
        elif not tile.walkable:
            raise ValueError("Structures require walkable terrain.")
        if any(
            resource.x == x
            and resource.y == y
            and not resource.depleted
            and resource.resource_type
            in {ResourceType.TREE, ResourceType.STONE, ResourceType.ORE}
            for resource in world.resources.values()
        ):
            raise ValueError("Clear solid resources before placing construction.")
        if any(
            structure.x == x and structure.y == y
            for structure in world.structures.values()
        ):
            raise ValueError("A structure already occupies this tile.")
        self.validate_space(world, structure_type, x, y)
        requirements, work_required = self.BLUEPRINTS[structure_type]
        structure = Structure(
            structure_type=structure_type,
            footprint_version=2,
            x=x,
            y=y,
            builder_id=actor_id,
            work_required=work_required,
            materials_required=requirements.copy(),
            bed_capacity={StructureType.SHELTER: 4, StructureType.TENT: 2}.get(
                structure_type, 0
            ),
        )
        world.structures[str(structure.id)] = structure
        return structure

    def deliver_materials(self, structure_id: UUID, actor_id: str) -> dict[str, float]:
        """Transfers only currently missing construction supplies from one pack."""
        world = self._require_world()
        site = self._structure(structure_id)
        actor = world.entities.get(actor_id)
        inventory = world.inventories.get(actor_id)
        if site.completed:
            raise ValueError(
                "Completed structures no longer accept construction supplies."
            )
        if actor is None or not actor.active or inventory is None:
            raise ValueError("An active citizen with an inventory is required.")
        if abs(actor.x - site.x) + abs(actor.y - site.y) > 1:
            raise ValueError("Citizen must be beside the construction site.")
        delivered: dict[str, float] = {}
        for material, missing in site.missing_materials.items():
            amount = min(missing, inventory.items.get(material, 0.0))
            if amount <= 0:
                continue
            inventory.consume({material: amount})
            site.materials_delivered[material] = (
                site.materials_delivered.get(material, 0.0) + amount
            )
            delivered[material] = amount
        if not delivered:
            raise ValueError("Citizen is not carrying a material this site needs.")
        return delivered

    def apply_work(self, structure_id: UUID, actor_id: str, amount: float) -> Structure:
        """Applies bounded work to an unfinished construction site."""
        if not actor_id.strip():
            raise ValueError("Actor ID cannot be empty.")
        structure = self._structure(structure_id)
        if structure.completed:
            raise ValueError("Structure is already complete.")
        if not structure.funded:
            raise ValueError("Construction site is waiting for delivered materials.")
        structure.apply_work(amount)
        if structure.completed and structure.structure_type == StructureType.BRIDGE:
            tile = self._require_world().retrieve_tile(structure.x, structure.y)
            tile.walkable = True
        return structure

    def blueprints(self) -> dict[str, dict[str, object]]:
        """Returns all currently supported construction recipes."""
        return {
            kind.value.lower(): {"materials": materials, "work_required": work,
                "ground_tiles": 4 if kind in {StructureType.SHELTER, StructureType.TENT, StructureType.STORAGE, StructureType.FARM} else 1,
                "entrance_required": kind not in {StructureType.ROAD, StructureType.BRIDGE, StructureType.FARM, StructureType.CAMPFIRE, StructureType.TORCH}}
            for kind, (materials, work) in self.BLUEPRINTS.items()
        }

    def transfer_storage(
        self,
        structure_id: UUID,
        actor_id: str,
        item: str,
        amount: float,
        withdraw: bool = False,
    ) -> float:
        """Moves material between a nearby citizen and a completed communal store."""
        world = self._require_world()
        store = self._structure(structure_id)
        actor = world.entities.get(actor_id)
        household_store = store.bed_capacity > 0 and actor_id in store.resident_ids
        if (store.structure_type != StructureType.STORAGE and not household_store) or not store.completed:
            raise ValueError("A completed storage building is required.")
        if actor is None or not actor.active:
            raise ValueError("An active citizen is required.")
        if abs(actor.x - store.x) + abs(actor.y - store.y) > 1:
            raise ValueError("Citizen must be beside storage.")
        if not isfinite(amount) or amount <= 0:
            raise ValueError("Transfer amount must be finite and positive.")
        pack = world.inventories.get(actor_id)
        if pack is None:
            raise ValueError("Citizen has no inventory.")
        source, destination = (
            (store.stockpile, pack) if withdraw else (pack, store.stockpile)
        )
        transferred = min(
            amount,
            source.items.get(item, 0),
            destination.capacity - destination.carried,
        )
        if transferred <= 0:
            raise ValueError("No material or destination capacity is available.")
        source.consume({item: transferred})
        destination.add(item, transferred)
        return transferred

    def _structure(self, structure_id: UUID) -> Structure:
        structure = self._require_world().structures.get(str(structure_id))
        if structure is None:
            raise LookupError("Structure does not exist.")
        return structure

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
