"""KPIs aggreges pour le dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Query

import pandas as pd

from ..config import parse_date
from ..data.loader import get_store

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("")
def overview(now: str | None = Query(None)):
    ds = get_store()
    now_d = parse_date(now)
    now_ts = pd.Timestamp(now_d)

    latest = ds.latest_stock_at(now_d)
    n_skus = int(len(latest))
    if not latest.empty:
        # Rupture = stock <= seuil_min OU couverture reelle < 2 jours.
        rupture_flag = (latest["risque_rupture"] == 1) | (latest["jours_couverture_reel"] < 2)
        surstock_flag = latest["risque_surstock"] == 1
        n_ruptures = int(rupture_flag.sum())
        n_surstocks = int(surstock_flag.sum())
    else:
        n_ruptures = n_surstocks = 0
    taux_service = round(1 - (n_ruptures / max(n_skus, 1)), 3)

    if not latest.empty:
        latest = latest.assign(_rupture_flag=rupture_flag.astype(int),
                               _surstock_flag=surstock_flag.astype(int))
        by_cat = (
            latest.groupby("categorie")
            .agg(skus=("product_id", "count"),
                 ruptures=("_rupture_flag", "sum"),
                 surstocks=("_surstock_flag", "sum"))
            .reset_index()
            .to_dict(orient="records")
        )
    else:
        by_cat = []

    # Bilan commercial cumule des 3 derniers mois <= now
    bilan = ds.bilan.copy()
    bilan = bilan[bilan["periode"] <= now_ts].sort_values("periode")
    last_period = bilan["periode"].max() if not bilan.empty else None
    if last_period is not None:
        recent = bilan[bilan["periode"] >= (last_period - pd.DateOffset(months=2))]
        ca_total = float(recent["chiffre_affaires"].sum())
        marge_total = float(recent["marge_brute"].sum())
        taux_marge = round(marge_total / max(ca_total, 1), 3) if ca_total else 0.0
        avg_taux_rupture = round(float(recent["taux_rupture"].mean()), 3)
        avg_taux_surstock = round(float(recent["taux_surstock"].mean()), 3)
    else:
        ca_total = marge_total = 0.0
        taux_marge = avg_taux_rupture = avg_taux_surstock = 0.0

    if not latest.empty:
        ok_count = int(((~rupture_flag) & (~surstock_flag)).sum())
    else:
        ok_count = 0
    status = {"ok": ok_count, "rupture": n_ruptures, "surstock": n_surstocks}

    return {
        "now": str(now_d),
        "skus_total": n_skus,
        "ruptures": n_ruptures,
        "surstocks": n_surstocks,
        "taux_service": taux_service,
        "ca_3m": round(ca_total, 2),
        "marge_3m": round(marge_total, 2),
        "taux_marge_3m": taux_marge,
        "taux_rupture_3m": avg_taux_rupture,
        "taux_surstock_3m": avg_taux_surstock,
        "by_categorie": by_cat,
        "status": status,
    }


@router.get("/timeseries")
def timeseries(now: str | None = Query(None)):
    """Serie temporelle des KPIs (par mois) pour graphiques."""
    ds = get_store()
    now_d = parse_date(now)
    now_ts = pd.Timestamp(now_d)
    bilan = ds.bilan[ds.bilan["periode"] <= now_ts].copy()
    if bilan.empty:
        return {"series": []}
    g = (
        bilan.groupby("periode")
        .agg(
            ca=("chiffre_affaires", "sum"),
            marge=("marge_brute", "sum"),
            taux_rupture=("taux_rupture", "mean"),
            taux_surstock=("taux_surstock", "mean"),
        )
        .reset_index()
        .sort_values("periode")
    )
    return {
        "series": [
            {
                "month": str(r["periode"].date()),
                "ca": round(float(r["ca"]), 2),
                "marge": round(float(r["marge"]), 2),
                "taux_rupture": round(float(r["taux_rupture"]), 3),
                "taux_surstock": round(float(r["taux_surstock"]), 3),
            }
            for _, r in g.iterrows()
        ]
    }
