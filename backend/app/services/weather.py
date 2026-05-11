"""Client Open-Meteo (gratuit, sans cle) avec cache memoire 15 min."""
from __future__ import annotations

import json
import time
from urllib.error import URLError
from urllib.request import urlopen

CITY_COORDS = {
    "Paris":     (48.8566,  2.3522),
    "Lyon":      (45.7640,  4.8357),
    "Marseille": (43.2965,  5.3698),
    "Lille":     (50.6292,  3.0573),
    "Toulouse":  (43.6047,  1.4442),
    "Nice":      (43.7102,  7.2620),
    "Bordeaux":  (44.8378, -0.5792),
    "Nantes":    (47.2184, -1.5536),
}

# Codes WMO -> libelle lisible
WEATHER_CODES: dict[int, str] = {
    0: "Soleil", 1: "Voile", 2: "Partiellement nuageux", 3: "Nuageux",
    45: "Brouillard", 48: "Brouillard givrant",
    51: "Bruine legere", 53: "Bruine", 55: "Bruine forte",
    61: "Pluie legere", 63: "Pluie", 65: "Pluie forte",
    71: "Neige legere", 73: "Neige", 75: "Neige forte",
    77: "Gresil",
    80: "Averses", 81: "Averses fortes", 82: "Averses violentes",
    85: "Averses neige", 86: "Averses neige fortes",
    95: "Orage", 96: "Orage grele", 99: "Orage violent",
}

CACHE_TTL = 900  # 15 min
_cache: dict[str, tuple[float, dict]] = {}


def _to_label(code: int | None) -> str:
    if code is None:
        return "Inconnu"
    return WEATHER_CODES.get(int(code), "Inconnu")


def get_weather(city: str) -> dict | None:
    """Retourne meteo actuelle + prevision 4 jours pour une ville cible."""
    if city not in CITY_COORDS:
        return None
    now = time.time()
    cached = _cache.get(city)
    if cached and (now - cached[0]) < CACHE_TTL:
        return cached[1]

    lat, lon = CITY_COORDS[city]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&forecast_days=4&timezone=Europe/Paris"
    )
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (URLError, OSError, json.JSONDecodeError):
        return cached[1] if cached else None  # stale ok

    current = data.get("current") or {}
    daily = data.get("daily") or {}
    times = daily.get("time") or []
    out = {
        "city": city,
        "lat": lat,
        "lon": lon,
        "current": {
            "temp_c": round(float(current.get("temperature_2m", 0)), 1),
            "weather_code": current.get("weather_code"),
            "conditions": _to_label(current.get("weather_code")),
            "wind_kmh": round(float(current.get("wind_speed_10m", 0)), 1),
            "humidity_pct": int(current.get("relative_humidity_2m") or 0),
        },
        "forecast": [
            {
                "date": times[i],
                "temp_max": round(float((daily.get("temperature_2m_max") or [0])[i]), 1),
                "temp_min": round(float((daily.get("temperature_2m_min") or [0])[i]), 1),
                "precipitation_mm": float((daily.get("precipitation_sum") or [0])[i]),
                "conditions": _to_label((daily.get("weather_code") or [0])[i]),
            }
            for i in range(min(len(times), 4))
        ],
        "fetched_at": now,
        "source": "Open-Meteo",
    }
    _cache[city] = (now, out)
    return out


def get_all_weather() -> list[dict]:
    out: list[dict] = []
    for city in CITY_COORDS:
        w = get_weather(city)
        if w:
            out.append(w)
    return out


def cache_age_seconds() -> float | None:
    """Age du cache le plus recent (pour l'indicateur 'live')."""
    if not _cache:
        return None
    return time.time() - max(ts for ts, _ in _cache.values())
