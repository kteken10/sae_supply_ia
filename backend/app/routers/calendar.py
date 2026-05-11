"""Endpoint calendrier scolaire FR (data.gouv) + zones par ville."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import parse_date
from ..services.calendar_service import (
    CITY_TO_ZONE,
    all_records,
    get_vacances_for_city,
    source_info,
    upcoming_vacances_for_city,
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/info")
def info():
    return {
        "zones": CITY_TO_ZONE,
        **source_info(),
    }


@router.get("/vacances")
def vacances_summary(now: str | None = Query(None)):
    """Pour chaque ville, indique si elle est actuellement en vacances + prochaines vacances."""
    d = parse_date(now)
    out = []
    for city, zone in CITY_TO_ZONE.items():
        current = get_vacances_for_city(city, d)
        upcoming = upcoming_vacances_for_city(city, d, 2)
        out.append({
            "city": city,
            "zone": zone,
            "currently_on_vacation": bool(current),
            "current": current,
            "upcoming": upcoming,
        })
    return {"as_of": str(d), "items": out, **source_info()}


@router.get("/vacances/{city}")
def city_vacances(city: str, now: str | None = Query(None)):
    d = parse_date(now)
    return {
        "city": city,
        "zone": CITY_TO_ZONE.get(city),
        "as_of": str(d),
        "current": get_vacances_for_city(city, d),
        "upcoming": upcoming_vacances_for_city(city, d, 3),
    }


@router.get("/all")
def all_calendar():
    return {"records": all_records(), **source_info()}
