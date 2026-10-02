"""Households and a persistent settlement job board derived from world needs."""

from uuid import UUID

from app.domain.interfaces.world_repository import IWorldRepository
from app.domain.models.cognition import ActionType
from app.domain.models.entity import EntityKind
from app.domain.models.society import Household, SettlementJob
from app.domain.models.structure import StructureType
from app.domain.models.world import World


class SettlementService:
    """Connects homes, finite beds, facility requests, and active citizen work."""

    def __init__(self, repository: IWorldRepository) -> None:
        """Initializes settlement coordination against the active world."""
        self._repository = repository

    def advance_all(self, tick: int) -> None:
        """Refreshes households, useful jobs, and current job claims."""
        world = self._repository.get()
        if world is None:
            return
        self._assign_households(world, tick)
        desired = self._desired_jobs(world, tick)
        for key, job in list(world.settlement_jobs.items()):
            if key not in desired:
                job.status = "completed"
                job.claimed_by = None
        for key, job in desired.items():
            previous = world.settlement_jobs.get(key)
            if previous is not None:
                job.id = previous.id
                job.created_at_tick = previous.created_at_tick
            world.settlement_jobs[key] = job
        self._match_claims(world, tick)

    @staticmethod
    def _assign_households(world: World, tick: int) -> None:
        active_ids = {
            entity.id
            for entity in world.entities.values()
            if entity.active and entity.kind == EntityKind.AGENT
        }
        for home in world.structures.values():
            home.resident_ids = []
        for household in world.households.values():
            household.member_ids = []
        valid_home_ids: set[str] = set()
        for group in world.groups.values():
            members = sorted(
                (
                    member_id
                    for member_id in group.member_ids
                    if member_id in active_ids
                ),
                key=str,
            )
            homes = sorted(
                (
                    site
                    for site in world.structures.values()
                    if site.completed
                    and site.bed_capacity > 0
                    and (site.x - group.home_x) ** 2 + (site.y - group.home_y) ** 2
                    <= 144
                ),
                key=lambda site: (
                    (site.x - group.home_x) ** 2 + (site.y - group.home_y) ** 2,
                    str(site.id),
                ),
            )
            for home in homes:
                valid_home_ids.add(str(home.id))
                household_candidate = next(
                    (
                        item
                        for item in world.households.values()
                        if item.home_structure_id == home.id
                    ),
                    None,
                )
                if household_candidate is None:
                    household_candidate = Household(
                        group_id=group.id,
                        home_structure_id=home.id,
                        bed_capacity=home.bed_capacity,
                        created_at_tick=tick,
                    )
                    world.households[str(household_candidate.id)] = household_candidate
                household = household_candidate
                household.group_id = group.id
                household.bed_capacity = home.bed_capacity
                while members and len(household.member_ids) < household.bed_capacity:
                    member_id = members.pop(0)
                    household.member_ids.append(member_id)
                    home.resident_ids.append(str(member_id))
                    citizen = world.entities[str(member_id)]
                    citizen.metadata.update(
                        {
                            "household_id": str(household.id),
                            "assigned_home_id": str(home.id),
                            "bed_index": len(household.member_ids) - 1,
                            "homeless": False,
                        }
                    )
            for member_id in members:
                citizen = world.entities[str(member_id)]
                citizen.metadata.pop("household_id", None)
                citizen.metadata.pop("assigned_home_id", None)
                citizen.metadata.pop("bed_index", None)
                citizen.metadata["homeless"] = True
        for key, household in list(world.households.items()):
            if str(household.home_structure_id) not in valid_home_ids:
                world.households.pop(key)

    @staticmethod
    def _desired_jobs(world: World, tick: int) -> dict[str, SettlementJob]:
        jobs: dict[str, SettlementJob] = {}
        for site in world.structures.values():
            group = min(
                world.groups.values(),
                key=lambda item: (
                    (site.x - item.home_x) ** 2 + (site.y - item.home_y) ** 2,
                    str(item.id),
                ),
                default=None,
            )
            group_id = group.id if group is not None else None
            if not site.completed:
                for material, amount in site.missing_materials.items():
                    jobs[f"deliver:{site.id}:{material}"] = SettlementJob(
                        group_id=group_id,
                        job_type="deliver_construction",
                        target_id=str(site.id),
                        material=material,
                        amount=amount,
                        priority=1.05,
                        reason=(
                            f"Deliver {amount:.1f} {material} to the "
                            f"{site.structure_type.value.lower()} foundation."
                        ),
                        created_at_tick=tick,
                    )
                if site.funded:
                    jobs[f"build:{site.id}"] = SettlementJob(
                        group_id=group_id,
                        job_type="build",
                        target_id=str(site.id),
                        priority=0.9,
                        reason=(
                            f"Complete the funded "
                            f"{site.structure_type.value.lower()} construction."
                        ),
                        created_at_tick=tick,
                    )
            elif site.structure_type == StructureType.CAMPFIRE and site.fuel < 4:
                jobs[f"fuel:{site.id}"] = SettlementJob(
                    group_id=group_id,
                    job_type="fuel_fire",
                    target_id=str(site.id),
                    material="wood",
                    amount=4 - site.fuel,
                    priority=1.2 if site.fuel <= 0 else 0.75,
                    reason="Keep the communal fire warm through the next night.",
                    created_at_tick=tick,
                )
            elif site.structure_type == StructureType.FARM:
                task = "harvest_farm" if site.crop_food > 0 else "tend_farm"
                jobs[f"{task}:{site.id}"] = SettlementJob(
                    group_id=group_id,
                    job_type=task,
                    target_id=str(site.id),
                    priority=0.85 if site.crop_food > 0 else 0.55,
                    reason="Harvest ripe food."
                    if site.crop_food > 0
                    else "Plant and water the farm.",
                    created_at_tick=tick,
                )
        return jobs

    @staticmethod
    def _match_claims(world: World, tick: int) -> None:
        for entity in world.entities.values():
            entity.metadata.pop("settlement_job_id", None)
        for job in world.settlement_jobs.values():
            if job.status != "completed":
                job.status = "open"
                job.claimed_by = None
                job.claimed_at_tick = None
        for actor_id, action_id in world.active_actions.items():
            action = world.actions.get(action_id)
            if action is None:
                continue
            target_id = str(
                action.target.get("structure_id", action.target.get("supply_site", ""))
            )
            candidates = [
                job
                for job in world.settlement_jobs.values()
                if job.status == "open" and job.target_id == target_id
            ]
            if action.action_type == ActionType.BUILD:
                purpose = str(action.target.get("purpose", "build"))
                candidates = [
                    job
                    for job in candidates
                    if (purpose == "deliver")
                    == (job.job_type == "deliver_construction")
                ]
                if purpose == "deliver":
                    inventory = world.inventories.get(actor_id)
                    carried = inventory.items if inventory is not None else {}
                    relevant = [
                        job
                        for job in candidates
                        if job.material is not None
                        and carried.get(job.material, 0.0) > 0.0
                    ]
                    if relevant:
                        candidates = relevant
            elif action.target.get("purpose") == "fuel":
                candidates = [job for job in candidates if job.job_type == "fuel_fire"]
            else:
                continue
            if not candidates:
                continue
            chosen = max(candidates, key=lambda job: (job.priority, str(job.id)))
            chosen.status = "claimed"
            chosen.claimed_by = UUID(actor_id)
            chosen.claimed_at_tick = tick
            actor = world.entities.get(actor_id)
            if actor is not None:
                actor.metadata["settlement_job_id"] = str(chosen.id)
