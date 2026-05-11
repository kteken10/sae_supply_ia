"""Endpoint meteo live (Open-Meteo)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.weather import (
    CITY_COORDS,
    cache_age_seconds,
    get_all_weather,
    get_weather,
)

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("")
def all_weather():
    items = get_all_weather()
    return {
        "weather": items,
        "count": len(items),
        "source": "Open-Meteo (https://open-meteo.com) - no auth, free",
        "cache_age_s": cache_age_seconds(),
    }


@router.get("/cities")
def supported_cities():
    return {"cities": list(CITY_COORDS.keys())}


@router.get("/{city}")
def city_weather(city: str):
    w = get_weather(city)
    if not w:
        raise HTTPException(status_code=404, detail=f"Ville '{city}' non supportee ou meteo indisponible")
    return w
