"""Deterministic utility scoring from an entity's own state and knowledge."""

from app.application.services.construction_service import ConstructionService
from app.domain.models.cognition import GoalType, UtilityOption
from app.domain.models.entity import Entity, EntityKnowledge
from app.domain.models.inventory import Inventory
from app.domain.models.structure import StructureType


class UtilityService:
    """Ranks motives without accessing undiscovered world state."""

    @staticmethod
    def building_priorities(
        entity: Entity, inventory: Inventory
    ) -> tuple[StructureType, ...]:
        """Orders useful projects from current pressure, not a fixed tech sequence."""
        needs = entity.needs
        scores = {
            StructureType.SHELTER: 0.6,
            StructureType.CAMPFIRE: 0.3,
            StructureType.STORAGE: inventory.carried / inventory.capacity,
            StructureType.WORKBENCH: 0.2,
            StructureType.WELL: (needs.thirst / 100.0 if needs else 0.0),
            StructureType.FARM: (needs.hunger / 100.0 if needs else 0.0),
        }
        if needs and needs.body_temperature_c < 36.5:
            scores[StructureType.CAMPFIRE] = 1.0
            scores[StructureType.SHELTER] = 0.95
        return tuple(sorted(scores, key=lambda kind: (-scores[kind], kind.value)))

    @staticmethod
    def evaluate(
        entity: Entity, knowledge: EntityKnowledge, inventory: Inventory
    ) -> list[UtilityOption]:
        """Returns all candidate goals sorted by descending utility."""
        if entity.needs is None:
            return []
        needs = entity.needs
        carried_edible = sum(
            inventory.items.get(item, 0.0) for item in ("food", "fruit", "mushroom")
        )
        food_bonus = 0.12 if carried_edible > 0.0 else 0.0
        axe_recipe = {"wood": 2.0, "stone": 3.0}
        can_craft_axe = inventory.items.get("stone_axe", 0.0) < 1.0 and inventory.has(
            axe_recipe
        )
        pickaxe_recipe = {"wood": 2.0, "stone": 4.0}
        basket_recipe = {"fiber": 6.0}
        can_craft_pickaxe = inventory.items.get(
            "stone_pickaxe", 0.0
        ) < 1.0 and inventory.has(pickaxe_recipe)
        can_craft_basket = inventory.items.get("basket", 0.0) < 1.0 and inventory.has(
            basket_recipe
        )
        can_craft_tool = can_craft_axe or can_craft_pickaxe or can_craft_basket
        known_structure_types = {
            str(record.data.get("type", ""))
            for record in knowledge.structures.values()
            if not (
                record.data.get("type") == "storage" and record.data.get("storage_full")
            )
        }
        next_structure = next(
            (
                (
                    structure_type.value.lower(),
                    ConstructionService.BLUEPRINTS[structure_type][0],
                )
                for structure_type in UtilityService.building_priorities(
                    entity, inventory
                )
                if structure_type.value.lower() not in known_structure_types
            ),
            None,
        )
        can_build_structure = next_structure is not None and inventory.has(
            next_structure[1]
        )
        free_capacity = max(0.0, inventory.capacity - inventory.carried)
        options = [
            UtilityOption(
                goal_type=GoalType.SATISFY_THIRST,
                score=needs.thirst / 100.0 * 1.35,
                reason=f"Thirst pressure is {needs.thirst:.1f}/100.",
            ),
            UtilityOption(
                goal_type=GoalType.SATISFY_HUNGER,
                score=min(1.5, needs.hunger / 100.0 * 1.2 + food_bonus),
                reason=f"Hunger pressure is {needs.hunger:.1f}/100.",
            ),
            UtilityOption(
                goal_type=GoalType.REST,
                score=(100.0 - needs.energy) / 100.0,
                reason=f"Energy has fallen to {needs.energy:.1f}/100.",
            ),
            UtilityOption(
                goal_type=GoalType.SEEK_SAFETY,
                score=(100.0 - needs.safety) / 100.0 * 1.15,
                reason=f"Safety has fallen to {needs.safety:.1f}/100.",
            ),
            UtilityOption(
                goal_type=GoalType.GATHER,
                score=0.52
                if (knowledge.resources or "storage" in known_structure_types)
                and free_capacity >= 1.0
                else 0.0,
                reason=(
                    f"{len(knowledge.resources)} resources are known and "
                    f"{free_capacity:.1f} carrying capacity remains."
                    if free_capacity >= 1.0
                    else "Inventory is full; gathering is not currently useful."
                ),
            ),
            UtilityOption(
                goal_type=GoalType.CRAFT,
                score=0.74 if can_craft_tool else 0.0,
                reason="Materials are available for the next useful tool."
                if can_craft_tool
                else "No useful tool recipe is currently affordable.",
            ),
            UtilityOption(
                goal_type=GoalType.BUILD,
                score=0.82 if can_build_structure else 0.0,
                reason=(
                    f"Materials are ready for a {next_structure[0]}."
                    if can_build_structure and next_structure is not None
                    else "Materials for the next settlement structure are incomplete."
                ),
            ),
            UtilityOption(
                goal_type=GoalType.EXPLORE,
                score=0.30 if not knowledge.resources else 0.16,
                reason=f"Only {len(knowledge.tiles)} tiles are known.",
            ),
        ]
        return sorted(options, key=lambda item: (-item.score, item.goal_type.value))
