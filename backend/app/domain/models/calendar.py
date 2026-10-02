"""Deterministic simulation calendar derived from the authoritative tick."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Season(StrEnum):
    """The four initial world seasons."""

    SPRING = "SPRING"
    SUMMER = "SUMMER"
    AUTUMN = "AUTUMN"
    WINTER = "WINTER"


class DayPhase(StrEnum):
    """Visual phases of one simulation day."""

    DAWN = "DAWN"
    DAY = "DAY"
    DUSK = "DUSK"
    NIGHT = "NIGHT"


class WeatherType(StrEnum):
    """Initial observable weather conditions."""

    CLEAR = "CLEAR"
    RAIN = "RAIN"
    SNOW = "SNOW"


class CalendarSnapshot(BaseModel):
    """Calendar state corresponding to one simulation tick."""

    day: int
    hour: int
    season: Season
    phase: DayPhase
    weather: WeatherType
    weather_intensity: float
    temperature_c: float
    feels_like_c: float
    humidity: float
    cloud_cover: float
    pressure_hpa: float
    daylight: float
    wind_speed: float
    wind_direction: float
    precipitation_center_x: float
    precipitation_center_y: float
    precipitation_radius: int


class CalendarControl(BaseModel):
    """Runtime environment controls owned by the authoritative simulation."""

    ticks_per_day: int = Field(default=24, ge=12, le=480)
    day_start_hour: int = Field(default=8, ge=2, le=12)
    night_start_hour: int = Field(default=20, ge=16, le=23)
    hour_offset: int = Field(default=0, ge=0, le=23)
    season_override: Season | None = None
    weather_override: WeatherType | None = None
    weather_intensity_override: float | None = Field(default=None, ge=0.0, le=1.0)
    temperature_override_c: float | None = Field(default=None, ge=-60.0, le=60.0)
    wind_speed_override: float | None = Field(default=None, ge=0.0, le=40.0)
    wind_direction_override: float | None = Field(default=None, ge=0.0, lt=360.0)
    precipitation_radius_override: int | None = Field(default=None, ge=2, le=64)


_calendar_control = CalendarControl()


def get_calendar_control() -> CalendarControl:
    """Returns a copy so API callers cannot mutate global state accidentally."""
    return _calendar_control.model_copy(deep=True)


def reset_calendar_control() -> CalendarControl:
    """Restores deterministic automatic calendar and weather behavior."""
    global _calendar_control
    _calendar_control = CalendarControl()
    return get_calendar_control()


def configure_calendar_control(
    tick: int,
    control: CalendarControl,
    current_hour: int | None = None,
) -> CalendarControl:
    """Applies validated runtime controls and optionally aligns the current hour."""
    global _calendar_control
    if control.night_start_hour - control.day_start_hour < 6:
        raise ValueError("Daytime must be at least six hours long.")
    if current_hour is not None:
        if not 0 <= current_hour <= 23:
            raise ValueError("Current hour must be between 0 and 23.")
        natural_hour = int(tick * 24 / control.ticks_per_day + 6) % 24
        offset = (current_hour - natural_hour) % 24
        control = control.model_copy(update={"hour_offset": offset})
    _calendar_control = control.model_copy(deep=True)
    return get_calendar_control()


def calendar_at_tick(tick: int) -> CalendarSnapshot:
    """Returns a reproducible calendar snapshot for a tick."""
    control = _calendar_control
    total_hours = int(tick * 24 / control.ticks_per_day) + 6 + control.hour_offset
    hour = total_hours % 24
    total_days = total_hours // 24
    season = control.season_override or list(Season)[(total_days // 30) % len(Season)]

    if control.day_start_hour - 2 <= hour < control.day_start_hour:
        phase = DayPhase.DAWN
    elif control.day_start_hour <= hour < control.night_start_hour - 2:
        phase = DayPhase.DAY
    elif control.night_start_hour - 2 <= hour < control.night_start_hour:
        phase = DayPhase.DUSK
    else:
        phase = DayPhase.NIGHT

    day = total_days + 1
    weather = WeatherType.CLEAR
    intensity = 0.0
    if season == Season.WINTER and day % 3 != 0:
        weather = WeatherType.SNOW
        intensity = 0.45 + (day % 4) * 0.12
    elif season != Season.WINTER and day % 4 == 1:
        weather = WeatherType.RAIN
        intensity = 0.4 + (day % 3) * 0.15
    if control.weather_override is not None:
        weather = control.weather_override
        intensity = 0.0 if weather == WeatherType.CLEAR else 0.65
    if control.weather_intensity_override is not None:
        intensity = control.weather_intensity_override

    seasonal_temperature = {
        Season.SPRING: 16.0,
        Season.SUMMER: 27.0,
        Season.AUTUMN: 13.0,
        Season.WINTER: -3.0,
    }[season]
    daily_temperature = -5.0 * abs(hour - 14) / 14.0 + 3.0
    temperature = seasonal_temperature + daily_temperature
    if weather == WeatherType.RAIN:
        temperature -= 2.5
    elif weather == WeatherType.SNOW:
        temperature = min(temperature, -0.5)
    if control.temperature_override_c is not None:
        temperature = control.temperature_override_c

    wind_speed = 4.0 + ((day * 7 + hour * 3) % 12) * 0.65
    wind_direction = float((day * 37 + hour * 11) % 360)
    if control.wind_speed_override is not None:
        wind_speed = control.wind_speed_override
    if control.wind_direction_override is not None:
        wind_direction = control.wind_direction_override
    daylight = max(0.0, 1.0 - abs(hour - 12.0) / 8.0)
    humidity = {
        Season.SPRING: 0.62,
        Season.SUMMER: 0.48,
        Season.AUTUMN: 0.58,
        Season.WINTER: 0.44,
    }[season]
    humidity += 0.24 if weather in {WeatherType.RAIN, WeatherType.SNOW} else 0.0
    humidity += max(0.0, 0.08 - daylight * 0.08)
    humidity = min(humidity, 0.98)
    cloud_cover = {
        WeatherType.CLEAR: 0.12,
        WeatherType.RAIN: 0.78,
        WeatherType.SNOW: 0.86,
    }[weather]
    pressure_hpa = 1020.0 - cloud_cover * 17.0 + ((day * 13 + hour) % 7 - 3)
    wind_chill = max(0.0, wind_speed - 5.0) * (0.12 if temperature < 12.0 else 0.04)
    humidity_heat = max(0.0, temperature - 24.0) * humidity * 0.12
    feels_like = temperature - wind_chill + humidity_heat
    precipitation_center_x = 0.2 + float((day * 17) % 60) / 100.0
    precipitation_center_y = 0.2 + float((day * 29) % 60) / 100.0
    precipitation_radius = 8 + (day % 7)
    if control.precipitation_radius_override is not None:
        precipitation_radius = control.precipitation_radius_override

    return CalendarSnapshot(
        day=day,
        hour=hour,
        season=season,
        phase=phase,
        weather=weather,
        weather_intensity=min(intensity, 1.0),
        temperature_c=round(temperature, 1),
        feels_like_c=round(feels_like, 1),
        humidity=round(humidity, 2),
        cloud_cover=cloud_cover,
        pressure_hpa=round(pressure_hpa, 1),
        daylight=round(daylight, 2),
        wind_speed=round(wind_speed, 1),
        wind_direction=wind_direction,
        precipitation_center_x=precipitation_center_x,
        precipitation_center_y=precipitation_center_y,
        precipitation_radius=precipitation_radius,
    )
