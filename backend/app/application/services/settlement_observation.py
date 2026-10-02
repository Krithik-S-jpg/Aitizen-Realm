"""Read-only settlement reports derived from live workers and nearby facilities."""

from app.domain.models.entity import EntityKind
from app.domain.models.structure import StructureType
from app.domain.models.world import World


def settlement_reports(world: World) -> list[dict[str, object]]:
    """Never invent jobs, stock or progress; active actions are the job ledger."""
    reports: list[dict[str, object]] = []
    groups = list(world.groups.values())
    for group in groups:
        members = [
            entity
            for entity in world.entities.values()
            if entity.active
            and entity.kind == EntityKind.AGENT
            and entity.id in group.member_ids
        ]
        sites = [
            site
            for site in world.structures.values()
            if (site.x - group.home_x) ** 2 + (site.y - group.home_y) ** 2 <= 144
            and min(
                groups,
                key=lambda item: (
                    (site.x - item.home_x) ** 2 + (site.y - item.home_y) ** 2,
                    str(item.id),
                ),
            ).id
            == group.id
        ]
        stock: dict[str, float] = {}
        carried: dict[str, float] = {}
        for site in sites:
            for material, amount in site.stockpile.items.items():
                stock[material] = stock.get(material, 0) + amount
        for member in members:
            inventory = world.inventories.get(str(member.id))
            if inventory:
                for material, amount in inventory.items.items():
                    carried[material] = carried.get(material, 0) + amount
        food = sum(
            stock.get(item, 0) + carried.get(item, 0)
            for item in ("food", "fruit", "meat", "mushroom")
        )
        shortages = []
        if members and food < len(members) * 2:
            shortages.append("Food reserve below one 2-unit meal per citizen")
        if members and not any(
            site.completed and site.structure_type == StructureType.SHELTER
            for site in sites
        ):
            shortages.append("No completed shelter nearby")
        if any(
            site.completed
            and site.structure_type == StructureType.CAMPFIRE
            and site.fuel < 1
            for site in sites
        ):
            shortages.append("A campfire needs fuel")
        jobs = []
        for member in members:
            action = world.actions.get(world.active_actions.get(str(member.id), ""))
            goal = world.goals.get(world.active_goals.get(str(member.id), ""))
            jobs.append(
                {
                    "citizen_id": str(member.id),
                    "name": member.name,
                    "activity": member.metadata.get("state", "idle")
                    if action is None
                    else action.action_type.value.lower(),
                    "target": action.target if action else {},
                    "progress": action.progress_ratio if action else None,
                    "reason": goal.reason
                    if goal
                    else member.metadata.get(
                        "blocked_reason",
                        member.metadata.get(
                            "last_decision_reason",
                            "Resting or waiting for a useful task",
                        ),
                    ),
                }
            )
        board = [
            job.model_dump(mode="json")
            for job in world.settlement_jobs.values()
            if job.group_id == group.id and job.status != "completed"
        ]
        households = [
            {
                **household.model_dump(mode="json"),
                "occupied_beds": len(household.member_ids),
                "available_beds": household.bed_capacity - len(household.member_ids),
            }
            for household in world.households.values()
            if household.group_id == group.id
        ]
        reports.append(
            {
                **group.model_dump(mode="json"),
                "active_members": len(members),
                "stock": stock,
                "carried": carried,
                "shortages": shortages,
                "jobs": jobs,
                "job_board": board,
                "households": households,
                "beds_total": sum(item["bed_capacity"] for item in households),
                "beds_available": sum(item["available_beds"] for item in households),
                "construction": [
                    {
                        "id": str(site.id),
                        "type": site.structure_type.value.lower(),
                        "completed": site.completed,
                        "progress": min(1, site.progress / site.work_required),
                        "funded": site.funded,
                        "missing_materials": site.missing_materials,
                    }
                    for site in sites
                ],
            }
        )
    return reports
