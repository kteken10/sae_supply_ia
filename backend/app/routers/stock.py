"""Endpoints stock & alertes."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query

from ..config import parse_date
from ..data.loader import get_store

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/snapshot")
def snapshot(now: str | None = Query(None),
             store_id: str | None = None,
             product_id: str | None = None):
    ds = get_store()
    now_d = parse_date(now)
    df = ds.latest_stock_at(now_d)
    if store_id:
        df = df[df["store_id"] == store_id]
    if product_id:
        df = df[df["product_id"] == product_id]
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    return {"now": str(now_d), "rows": rows, "count": len(rows)}


@router.get("/alerts")
def alerts(now: str | None = Query(None), max_items: int = 20):
    """SKU a risque (<48h ou rupture deja)."""
    ds = get_store()
    now_d = parse_date(now)
    df = ds.latest_stock_at(now_d)
    if df.empty:
        return {"now": str(now_d), "alerts": []}
    at_risk = df[(df["risque_rupture"] == 1) | (df["jours_couverture_reel"] < 5)].copy()
    at_risk = at_risk.sort_values("jours_couverture_reel").head(max_items)
    out = []
    for _, r in at_risk.iterrows():
        days = float(r["jours_couverture_reel"])
        out.append({
            "store_id": r["store_id"],
            "store_city": r["store_city"],
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "categorie": r["categorie"],
            "stock_actuel": int(r["stock_actuel"]),
            "seuil_min": int(r["seuil_min"]),
            "jours_couverture": round(days, 1),
            "urgence": "critical" if days < 2 else "high" if days < 5 else "medium",
        })
    return {"now": str(now_d), "alerts": out, "count": len(out)}


@router.get("/timeseries")
def stock_timeseries(store_id: str, product_id: str):
    """Historique des snapshots pour un (store, product)."""
    ds = get_store()
    df = ds.stock[(ds.stock["store_id"] == store_id) & (ds.stock["product_id"] == product_id)].copy()
    df = df.sort_values("date")
    return {
        "store_id": store_id,
        "product_id": product_id,
        "points": [
            {
                "date": pd.Timestamp(r["date"]).strftime("%Y-%m-%d"),
                "stock": int(r["stock_actuel"]),
                "seuil_min": int(r["seuil_min"]),
                "seuil_max": int(r["seuil_max"]),
                "rupture": int(r["risque_rupture"]),
                "surstock": int(r["risque_surstock"]),
            }
            for _, r in df.iterrows()
        ],
    }
