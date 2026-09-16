"""Emergent relationships, skill specialization, and group formation."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.society import Profession, SocialBond, SocialGroup
from app.domain.models.world import World


class SocietyService:
    """Advances small-scale social organization without global agent knowledge."""

    GROUP_RANGE = 5

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes social state against the shared world."""
        self._repository = repository

    def register_interaction(
        self, source_id: UUID, target_id: UUID, tick: int, positive: bool = True
    ) -> SocialBond:
        """Creates or updates a directional social bond."""
        world = self._require_world()
        self._entity(world, source_id)
        self._entity(world, target_id)
        key = f"{source_id}:{target_id}"
        bond = world.social_bonds.setdefault(
            key, SocialBond(source_id=source_id, target_id=target_id)
        )
        bond.interact(tick, 0.035 if positive else -0.08)
        return bond

    def advance_all(self, tick: int) -> None:
        """Infers professions and forms stable local groups when agents coexist."""
        world = self._require_world()
        agents = sorted(
            (
                entity
                for entity in world.entities.values()
                if entity.active and entity.kind == EntityKind.AGENT
            ),
            key=lambda entity: str(entity.id),
        )
        for entity in agents:
            entity.profession = self._profession_for(entity)
        ungrouped = [entity for entity in agents if entity.group_id is None]
        if len(ungrouped) < 2:
            return
        founder = ungrouped[0]
        nearby = [
            entity
            for entity in ungrouped
            if founder.distance_squared_to(entity.x, entity.y) <= self.GROUP_RANGE**2
        ]
        if len(nearby) < 2:
            return
        group = SocialGroup(
            name=f"Settlement {len(world.groups) + 1}",
            founder_id=founder.id,
            member_ids=[entity.id for entity in nearby],
            home_x=founder.x,
            home_y=founder.y,
            formed_at_tick=tick,
        )
        world.groups[str(group.id)] = group
        for entity in nearby:
            entity.group_id = group.id

    def overview(self) -> dict[str, object]:
        """Returns groups and relationships for administration and analysis."""
        world = self._require_world()
        return {
            "groups": [
                group.model_dump(mode="json") for group in world.groups.values()
            ],
            "relationships": [
                bond.model_dump(mode="json") for bond in world.social_bonds.values()
            ],
        }

    def relationships_for(self, entity_id: UUID) -> list[SocialBond]:
        """Returns typed relationships involving one known entity."""
        world = self._require_world()
        self._entity(world, entity_id)
        return [
            bond
            for bond in world.social_bonds.values()
            if entity_id in {bond.source_id, bond.target_id}
        ]

    @staticmethod
    def add_skill_experience(entity: Entity, skill: str, amount: float) -> None:
        """Adds bounded practical experience to an entity skill."""
        entity.skills[skill] = min(100.0, entity.skills.get(skill, 0.0) + amount)

    @staticmethod
    def _profession_for(entity: Entity) -> Profession:
        if not entity.skills or max(entity.skills.values(), default=0.0) < 10.0:
            return Profession.GENERALIST
        skill = max(entity.skills, key=lambda key: (entity.skills[key], key))
        return {
            "foraging": Profession.FORAGER,
            "woodcutting": Profession.WOODCUTTER,
            "mining": Profession.MINER,
            "building": Profession.BUILDER,
            "crafting": Profession.CRAFTER,
            "exploration": Profession.EXPLORER,
        }.get(skill, Profession.GENERALIST)

    @staticmethod
    def _entity(world: World, entity_id: UUID) -> Entity:
        entity = world.entities.get(str(entity_id))
        if entity is None:
            raise LookupError("Entity does not exist.")
        return entity

    def _require_world(self) -> World:
        world = self._repository.get()
        if world is None:
            raise LookupError("No active world exists.")
        return world
