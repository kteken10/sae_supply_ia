"""Endpoint pour piloter les enrichissements (toggle ON/OFF)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import audit
from ..data.loader import get_store
from ..settings import get_settings, set_use_enriched

router = APIRouter(prefix="/api/settings", tags=["settings"])


class EnrichmentToggle(BaseModel):
    use_enriched: bool


@router.get("")
def current():
    s = get_settings()
    ds = get_store()
    return {
        "use_enriched": s.use_enriched,
        "has_enrichment_data": ds.has_enrichment,
        "available_enrichments": [
            "multi_suppliers (3 challengers per product, synthetic)",
            "holidays_fr (calendrier FR + Black Friday/Soldes)",
            "supplier_capacity (capacite mensuelle)",
            "category_storage_costs (cout stockage par categorie)",
            "climate_norms (meteo par ville x mois)",
            "bootstrap_RF (K=10 modeles)",
        ] if ds.has_enrichment else [],
    }


@router.post("")
def toggle(payload: EnrichmentToggle):
    s = set_use_enriched(payload.use_enriched)
    # Vide le cache forecast (les predictions changent selon use_enriched)
    from ..ml.forecast import _forecast_inner
    _forecast_inner.cache_clear()
    audit.append_event(
        "enrichment_toggle",
        {"use_enriched": s.use_enriched},
    )
    return {"use_enriched": s.use_enriched}
