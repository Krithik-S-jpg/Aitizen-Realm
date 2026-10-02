"""Transactional resource actions and actor-carried inventory."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.inventory import Inventory
from app.domain.models.resource import ResourceNode, ResourceType
from app.domain.models.world import World


class ResourceService:
    """Coordinates exclusive harvesting against the authoritative world."""

    MATERIAL_BY_RESOURCE = {
        ResourceType.TREE: "wood",
        ResourceType.STONE: "stone",
        ResourceType.PLANT: "food",
        ResourceType.BUSH: "food",
        ResourceType.MUSHROOM: "food",
        ResourceType.LOG: "wood",
        ResourceType.STUMP: "wood",
        ResourceType.REEDS: "fiber",
        ResourceType.LILY: "food",
        ResourceType.ORE: "ore",
        ResourceType.CLAY: "clay",
        ResourceType.CACTUS: "food",
        ResourceType.HERB: "herb",
        ResourceType.CARCASS: "meat",
    }
    CRAFTING_RECIPES: dict[str, dict[str, float]] = {
        "stone_axe": {"wood": 2.0, "stone": 3.0},
        "stone_pickaxe": {"wood": 2.0, "stone": 4.0},
        "basket": {"fiber": 6.0},
        "clay_pot": {"clay": 6.0},
        "iron_knife": {"wood": 1.0, "ore": 4.0},
    }

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes actions against the shared world repository."""
        self._repository = repository

    def inventory_for(self, actor_id: str) -> Inventory:
        """Returns or creates the inventory belonging to an actor."""
        world = self._require_world()
        return world.inventories.setdefault(actor_id, Inventory())

    def reserve(
        self, resource_id: UUID, actor_id: str, current_tick: int, duration_ticks: int
    ) -> ResourceNode:
        """Claims a resource for one actor until a simulation tick."""
        resource = self._resource(resource_id)
        if resource.depleted:
            raise ValueError("Cannot reserve a depleted resource.")
        resource.reserve(actor_id, current_tick, duration_ticks)
        return resource

    def release(self, resource_id: UUID, actor_id: str) -> ResourceNode:
        """Releases an actor-owned resource claim."""
        resource = self._resource(resource_id)
        resource.release(actor_id)
        return resource

    def gather(
        self, resource_id: UUID, actor_id: str, amount: float, current_tick: int
    ) -> tuple[ResourceNode, Inventory, float]:
        """Moves harvested material into the reserving actor's inventory."""
        resource = self._resource(resource_id)
        if not resource.is_reserved(current_tick) or resource.reserved_by != actor_id:
            raise ValueError("Actor must own an active reservation before gathering.")
        # Registered citizens must physically reach the node. Unbound actor
        # labels remain supported by the low-level resource administration API.
        if actor_id in self._require_world().entities:
            self._require_actor_in_reach(actor_id, resource)
            if resource.resource_type == ResourceType.TREE:
                raise ValueError("Chop the tree, then collect its fallen logs.")
        inventory = self.inventory_for(actor_id)
        available_capacity = max(0.0, inventory.capacity - inventory.carried)
        requested = min(amount, available_capacity)
        if requested <= 0.0:
            raise ValueError("Actor inventory is full.")
        gathered = resource.harvest(requested)
        material = self.MATERIAL_BY_RESOURCE[resource.resource_type]
        inventory.add(material, gathered)
        if resource.depleted:
            resource.release(actor_id)
        return resource, inventory, gathered

    def chop(
        self, resource_id: UUID, actor_id: str, amount: float, current_tick: int
    ) -> tuple[ResourceNode, Inventory, float]:
        """Fells a reachable tree; timber stays in the world until collected."""
        resource = self._resource(resource_id)
        if resource.resource_type != ResourceType.TREE:
            raise ValueError("Only a tree can be chopped.")
        self._require_actor_in_reach(actor_id, resource)
        if amount <= 0.0:
            raise ValueError("Requested amount must be greater than zero.")
        if resource.depleted or resource.visual_state == "fallen":
            raise ValueError("Tree has already been felled.")
        if resource.growth < 0.35:
            raise ValueError("Tree is too young to provide usable timber.")
        if not resource.is_reserved(current_tick):
            resource.reserve(actor_id, current_tick, 5)
        elif resource.reserved_by != actor_id:
            raise ValueError("Tree is reserved by another actor.")
        inventory = self.inventory_for(actor_id)
        chopped = resource.quantity
        timber = ResourceNode(
            resource_type=ResourceType.LOG,
            x=resource.x,
            y=resource.y,
            quantity=chopped,
            capacity=chopped,
            state_changed_tick=current_tick,
        )
        self._require_world().add_resource(timber)
        resource.quantity = 0.0
        resource.produce_quantity = 0.0
        resource.visual_state = "fallen"
        resource.state_changed_tick = current_tick
        resource.release(actor_id)
        return resource, inventory, chopped

    def pluck(
        self, resource_id: UUID, actor_id: str, amount: float
    ) -> tuple[ResourceNode, Inventory, float]:
        """Plucks renewable produce from a reachable living resource."""
        resource = self._resource(resource_id)
        self._require_actor_in_reach(actor_id, resource)
        inventory = self.inventory_for(actor_id)
        available_capacity = max(0.0, inventory.capacity - inventory.carried)
        requested = min(amount, available_capacity)
        if requested <= 0.0:
            raise ValueError("Actor inventory is full.")
        produce_type = resource.produce_type
        plucked = resource.pluck_produce(requested)
        inventory.add(str(produce_type), plucked)
        return resource, inventory, plucked

    def craft(self, actor_id: str, item_type: str) -> Inventory:
        """Crafts one known tool from carried materials."""
        world = self._require_world()
        actor = world.entities.get(actor_id)
        if actor is None or not actor.active:
            raise LookupError("Active actor entity does not exist.")
        recipe = self.CRAFTING_RECIPES.get(item_type)
        if recipe is None:
            raise LookupError("Crafting recipe does not exist.")
        inventory = self.inventory_for(actor_id)
        inventory.consume(recipe)
        accepted = inventory.add(item_type, 1.0)
        if accepted < 1.0:
            raise ValueError("Inventory has no room for the crafted item.")
        if item_type == "basket":
            inventory.capacity += 20.0
        return inventory

    def _require_actor_in_reach(self, actor_id: str, resource: ResourceNode) -> None:
        world = self._require_world()
        actor = world.entities.get(actor_id)
        if actor is None or not actor.active:
            raise LookupError("Active actor entity does not exist.")
        if actor.distance_squared_to(resource.x, resource.y) > 2:
            raise ValueError("Actor must stand on or beside the resource.")

    def _resource(self, resource_id: UUID) -> ResourceNode:
        world = self._require_world()
        resource = world.resources.get(str(resource_id))
        if resource is None:
            raise LookupError("Resource does not exist.")
        return resource

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
