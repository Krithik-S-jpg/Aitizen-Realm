"""Deterministic simulation calendar derived from the authoritative tick."""

from enum import StrEnum

from pydantic import BaseModel


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


def calendar_at_tick(tick: int) -> CalendarSnapshot:
    """Returns a reproducible calendar snapshot for a tick."""
    total_hours = tick + 6
    hour = total_hours % 24
    total_days = total_hours // 24
    season = list(Season)[(total_days // 30) % len(Season)]

    if 5 <= hour <= 7:
        phase = DayPhase.DAWN
    elif 8 <= hour <= 17:
        phase = DayPhase.DAY
    elif 18 <= hour <= 20:
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

    wind_speed = 4.0 + ((day * 7 + hour * 3) % 12) * 0.65
    wind_direction = float((day * 37 + hour * 11) % 360)
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
