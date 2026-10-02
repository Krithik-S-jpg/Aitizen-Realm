"""Regression coverage for lossless incremental event polling."""

from app.application.services.analytics_service import AnalyticsService
from app.domain.models.research import WorldEvent
from app.infrastructure.repositories.world_repository import InMemoryWorldRepository


def test_event_cursor_reads_every_retained_event_in_order() -> None:
    """A small polling page must not skip earlier retained events."""
    service = AnalyticsService(InMemoryWorldRepository())
    for index in range(12):
        service._record(
            str(index),
            WorldEvent(tick=index, event_type="test", title="Event", summary="Test"),
        )
    cursor = -1
    received = []
    while page := service.events(after_sequence=cursor, limit=5):
        received.extend(event.sequence for event in page)
        cursor = page[-1].sequence
    assert received == list(range(12))
