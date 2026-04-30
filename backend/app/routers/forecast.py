"""Endpoint forecast."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import parse_date
from ..ml.forecast import forecast as run_forecast

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def forecast_endpoint(
    store_id: str = Query(...),
    product_id: str = Query(...),
    now: str | None = Query(None),
    horizon_weeks: int = Query(4, ge=1, le=12),
):
    now_d = parse_date(now)
    try:
        result = run_forecast(store_id, product_id, str(now_d), horizon_weeks)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "store_id": store_id,
        "product_id": product_id,
        "now": str(now_d),
        "horizon_weeks": horizon_weeks,
        "history": result.history,
        "forecast": result.forecast,
        "metrics": {"mape": result.mape},
        "confidence": result.confidence,
        "n_train_points": result.n_train_points,
        "enrichments_used": result.enrichments_used,
    }
