"""Tests for deterministic day, night, and season progression."""

from app.domain.models.calendar import (
    DayPhase,
    Season,
    WeatherType,
    calendar_at_tick,
)


def test_calendar_progresses_through_day_phases() -> None:
    """Tick time deterministically advances through a 24-hour day."""
    assert calendar_at_tick(0).phase == DayPhase.DAWN
    assert calendar_at_tick(2).phase == DayPhase.DAY
    assert calendar_at_tick(12).phase == DayPhase.DUSK
    assert calendar_at_tick(18).phase == DayPhase.NIGHT
    assert calendar_at_tick(24).day == 2


def test_calendar_progresses_through_seasons() -> None:
    """Every thirty simulation days advances the season."""
    assert calendar_at_tick(0).season == Season.SPRING
    assert calendar_at_tick(24 * 30).season == Season.SUMMER
    assert calendar_at_tick(24 * 60).season == Season.AUTUMN
    assert calendar_at_tick(24 * 90).season == Season.WINTER


def test_weather_follows_calendar_and_season() -> None:
    """Spring can rain and winter produces deterministic snow."""
    assert calendar_at_tick(0).weather == WeatherType.RAIN
    assert calendar_at_tick(24 * 90).weather == WeatherType.SNOW
    assert calendar_at_tick(24 * 90).temperature_c <= 0.0
    assert calendar_at_tick(0).wind_speed > 0.0
    assert 0.0 <= calendar_at_tick(0).precipitation_center_x <= 1.0
    assert calendar_at_tick(0).precipitation_radius > 0
    assert 0.0 <= calendar_at_tick(0).humidity <= 1.0
    assert 0.0 <= calendar_at_tick(0).cloud_cover <= 1.0
    assert calendar_at_tick(0).pressure_hpa > 900.0
    assert 0.0 <= calendar_at_tick(0).daylight <= 1.0
