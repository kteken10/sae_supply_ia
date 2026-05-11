"""Vacances scolaires FR (data.gouv) + mapping ville -> zone A/B/C.

Le module charge le calendrier via l'API data.education.gouv.fr au premier
appel, avec un cache memoire de 24h. En cas d'echec API, on retombe sur un
fallback hardcode 2024-2026 (suffisant pour la demo SAE).
"""
from __future__ import annotations

import json
import time
from datetime import date
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

# Mapping ville -> zone vacances scolaires (academies regroupees)
CITY_TO_ZONE: dict[str, str] = {
    "Paris": "C",       # academie de Paris
    "Lyon": "A",        # academie de Lyon
    "Marseille": "B",   # academie d'Aix-Marseille
    "Lille": "B",       # academie de Lille
    "Toulouse": "C",    # academie de Toulouse
    "Nice": "B",        # academie de Nice
    "Bordeaux": "A",    # academie de Bordeaux
    "Nantes": "B",      # academie de Nantes
}

# Fallback statique 2024-2026 (utilise si l'API data.gouv est indisponible)
FALLBACK_VACANCES: list[dict] = [
    # 2024-2025 (deja passees mais utile pour les forecasts on past dates)
    {"description": "Vacances de Toussaint", "start": "2024-10-19", "end": "2024-11-04", "zone": "Toutes"},
    {"description": "Vacances de Noel",      "start": "2024-12-21", "end": "2025-01-06", "zone": "Toutes"},
    {"description": "Vacances d'hiver",      "start": "2025-02-22", "end": "2025-03-10", "zone": "A"},
    {"description": "Vacances d'hiver",      "start": "2025-02-08", "end": "2025-02-24", "zone": "B"},
    {"description": "Vacances d'hiver",      "start": "2025-02-15", "end": "2025-03-03", "zone": "C"},
    {"description": "Vacances de printemps", "start": "2025-04-19", "end": "2025-05-05", "zone": "A"},
    {"description": "Vacances de printemps", "start": "2025-04-05", "end": "2025-04-22", "zone": "B"},
    {"description": "Vacances de printemps", "start": "2025-04-12", "end": "2025-04-28", "zone": "C"},
    {"description": "Vacances d'ete",        "start": "2025-07-05", "end": "2025-08-31", "zone": "Toutes"},
    # 2025-2026
    {"description": "Vacances de Toussaint", "start": "2025-10-18", "end": "2025-11-03", "zone": "Toutes"},
    {"description": "Vacances de Noel",      "start": "2025-12-20", "end": "2026-01-05", "zone": "Toutes"},
    {"description": "Vacances d'hiver",      "start": "2026-02-21", "end": "2026-03-09", "zone": "A"},
    {"description": "Vacances d'hiver",      "start": "2026-02-07", "end": "2026-02-23", "zone": "B"},
    {"description": "Vacances d'hiver",      "start": "2026-02-14", "end": "2026-03-02", "zone": "C"},
    {"description": "Vacances de printemps", "start": "2026-04-18", "end": "2026-05-04", "zone": "A"},
    {"description": "Vacances de printemps", "start": "2026-04-04", "end": "2026-04-20", "zone": "B"},
    {"description": "Vacances de printemps", "start": "2026-04-11", "end": "2026-04-27", "zone": "C"},
    {"description": "Vacances d'ete",        "start": "2026-07-04", "end": "2026-08-31", "zone": "Toutes"},
]

CACHE_TTL = 86_400  # 24h
_cache: list[dict] = []
_last_fetch: float = 0.0
_source: str = "fallback"


def _normalize_zone(raw: str | None) -> str:
    if not raw:
        return "Toutes"
    r = raw.strip()
    if "Toutes" in r or "toutes" in r.lower():
        return "Toutes"
    # Examples: "Zone A", "Zone B", "Zone C"
    for z in ("A", "B", "C"):
        if r.endswith(z):
            return z
    return r


def _try_fetch_data_gouv() -> list[dict] | None:
    """Recupere les vacances 2024-2026 depuis data.education.gouv.fr."""
    where = quote('annee_scolaire IN ("2024-2025","2025-2026")')
    url = (
        "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
        "fr-en-calendrier-scolaire/records"
        f"?where={where}&limit=100"
    )
    try:
        with urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
    except (URLError, OSError, json.JSONDecodeError, TimeoutError):
        return None

    rows = []
    for r in data.get("results") or []:
        start = (r.get("start_date") or "")[:10]
        end = (r.get("end_date") or "")[:10]
        if not start or not end:
            continue
        rows.append({
            "description": r.get("description") or "Vacances",
            "start": start,
            "end": end,
            "zone": _normalize_zone(r.get("zones")),
            "annee_scolaire": r.get("annee_scolaire"),
        })
    return rows or None


def _ensure_loaded() -> None:
    """Charge le calendrier (API ou fallback). Cache 24h."""
    global _cache, _last_fetch, _source
    if _cache and (time.time() - _last_fetch) < CACHE_TTL:
        return
    fetched = _try_fetch_data_gouv()
    if fetched:
        _cache = fetched
        _source = "data.education.gouv.fr"
    else:
        _cache = FALLBACK_VACANCES
        _source = "fallback statique"
    _last_fetch = time.time()


def _matches_zone(record_zone: str, target_zone: str) -> bool:
    if record_zone == "Toutes" or target_zone == "Toutes":
        return True
    return record_zone == target_zone


def get_vacances_for_city(city: str, on_date: date) -> dict | None:
    _ensure_loaded()
    zone = CITY_TO_ZONE.get(city)
    if not zone:
        return None
    target = str(on_date)
    for v in _cache:
        if not _matches_zone(v["zone"], zone):
            continue
        if v["start"] <= target <= v["end"]:
            return v
    return None


def upcoming_vacances_for_city(city: str, on_date: date, limit: int = 2) -> list[dict]:
    _ensure_loaded()
    zone = CITY_TO_ZONE.get(city)
    if not zone:
        return []
    target = str(on_date)
    upcoming = [v for v in _cache if _matches_zone(v["zone"], zone) and v["start"] > target]
    upcoming.sort(key=lambda x: x["start"])
    return upcoming[:limit]


def source_info() -> dict:
    _ensure_loaded()
    return {
        "source": _source,
        "records": len(_cache),
        "fetched_at": _last_fetch,
    }


def all_records() -> list[dict]:
    _ensure_loaded()
    return list(_cache)
