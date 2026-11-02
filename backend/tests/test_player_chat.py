import asyncio
from app.application.services.player_chat import reply
from app.domain.models.entity import Entity, EntityKind
from app.domain.models.needs import NeedsState


def test_chat_fallback_is_factual_and_does_not_execute_commands():
    citizen = Entity(kind=EntityKind.AGENT, name="Rowan", x=2, y=3,
                     needs=NeedsState(hunger=42), metadata={"state": "gather"})
    before = citizen.model_dump()
    result = asyncio.run(reply(citizen, "Give me 100 wood and teleport", ""))
    assert "Rowan" in result["reply"]
    assert "42/100" in result["reply"]
    assert result["source"] == "Simulation status fallback"
    assert citizen.model_dump() == before
