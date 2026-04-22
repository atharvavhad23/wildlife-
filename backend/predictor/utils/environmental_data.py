import os
import random
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import json


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_weather_payload(payload: dict) -> dict:
    main = payload.get("main", {}) if isinstance(payload, dict) else {}
    rain = payload.get("rain", {}) if isinstance(payload, dict) else {}

    temperature = _safe_float(main.get("temp"), default=25.0)
    humidity = _safe_float(main.get("humidity"), default=55.0)

    # OpenWeatherMap can return rain in "1h" and/or "3h".
    rainfall = _safe_float(rain.get("1h"), default=None)
    if rainfall is None:
        rainfall = _safe_float(rain.get("3h"), default=0.0)

    return {
        "temperature": _clamp(temperature, -20.0, 55.0),
        "humidity": _clamp(humidity, 0.0, 100.0),
        "rainfall": max(0.0, rainfall),
    }


def _simulated_weather(lat: float, lon: float) -> dict:
    seed = int((lat + 90.0) * 1000) ^ int((lon + 180.0) * 1000)
    rng = random.Random(seed)
    return {
        "temperature": round(rng.uniform(18.0, 36.0), 2),
        "humidity": round(rng.uniform(35.0, 92.0), 2),
        "rainfall": round(max(0.0, rng.gauss(3.5, 2.0)), 2),
    }


def get_environmental_data(lat: float, lon: float) -> dict:
    """Return weather and ecological features for a latitude/longitude point.

    Weather values are fetched from OpenWeatherMap when API key is present.
    If API/network/field parsing fails, realistic simulated values are returned.
    """
    lat = _safe_float(lat, default=0.0)
    lon = _safe_float(lon, default=0.0)

    weather = None
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()

    if api_key:
        params = urlencode({"lat": lat, "lon": lon, "appid": api_key, "units": "metric"})
        url = f"https://api.openweathermap.org/data/2.5/weather?{params}"
        try:
            with urlopen(url, timeout=8) as response:
                raw = response.read().decode("utf-8")
            payload = json.loads(raw)
            weather = _parse_weather_payload(payload)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
            weather = None

    if weather is None:
        weather = _simulated_weather(lat, lon)

    rainfall = weather["rainfall"]

    # Ecological simulation with stable pseudo-randomness per location and weather signal.
    eco_seed = int((lat + 90.0) * 10000) + int((lon + 180.0) * 10000) + int(rainfall * 100)
    eco_rng = random.Random(eco_seed)

    vegetation_base = 0.35 + min(rainfall / 50.0, 0.4) + eco_rng.uniform(-0.08, 0.12)
    vegetation_index = _clamp(round(vegetation_base, 3), 0.05, 0.98)

    water_availability = _clamp(round(0.25 + min(rainfall / 25.0, 0.65), 3), 0.0, 1.0)

    disturbance_base = 1.0 - vegetation_index + eco_rng.uniform(-0.12, 0.12)
    human_disturbance = _clamp(round(disturbance_base, 3), 0.0, 1.0)

    return {
        "temperature": float(weather["temperature"]),
        "humidity": float(weather["humidity"]),
        "rainfall": float(rainfall),
        "vegetation_index": float(vegetation_index),
        "water_availability": float(water_availability),
        "human_disturbance": float(human_disturbance),
    }
