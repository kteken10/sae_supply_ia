"""
Forecast de demande (store x product).

Strategie:
  - Aggregation hebdomadaire (la donnee journaliere est sparse: ~106 obs/365 j).
  - Modele : RandomForest sur features [lag_1, lag_2, lag_4, month, weekofyear,
    promo_share, event_intensity]. Si l'enrichissement est actif, on injecte
    `event_intensity` issu du calendrier holidays_fr (Black Friday, Soldes,
    Noel, etc.).
  - Bootstrap : K=10 RF entraines sur des rééchantillonnages des résidus.
    On retourne la médiane + IQR -> intervalle de confiance plus stable que
    l'écart-type d'un seul modèle.
  - Intervalle 80% via la dispersion des K modèles ou les résidus si K=1.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from ..data.loader import get_store
from ..settings import get_settings

warnings.filterwarnings("ignore", category=FutureWarning)

K_BOOTSTRAP = 10  # Nombre de modeles dans l'ensemble


@dataclass
class ForecastResult:
    history: list
    forecast: list
    mape: float
    confidence: str
    n_train_points: int
    enrichments_used: list


def _aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    weekly = (
        df.set_index("date")
        .resample("W-MON")
        .agg(qty=("qty", "sum"), promo_share=("promo_share", "mean"))
        .reset_index()
    )
    weekly["qty"] = weekly["qty"].fillna(0.0)
    weekly["promo_share"] = weekly["promo_share"].fillna(0.0)
    return weekly


def _attach_event_intensity(weekly: pd.DataFrame, holidays: pd.DataFrame) -> pd.DataFrame:
    """Ajoute `event_intensity` = max d'intensite sur la semaine W-MON."""
    if holidays is None or holidays.empty:
        weekly["event_intensity"] = 0.0
        return weekly
    h = holidays.copy()
    h["week"] = h["date"].dt.to_period("W-MON").apply(lambda p: p.end_time.normalize())
    weekly_intensity = h.groupby("week")["intensite"].max().reset_index()
    weekly_intensity = weekly_intensity.rename(columns={"week": "date", "intensite": "event_intensity"})
    weekly_intensity["date"] = pd.to_datetime(weekly_intensity["date"]).dt.tz_localize(None)
    weekly = weekly.merge(weekly_intensity, on="date", how="left")
    weekly["event_intensity"] = weekly["event_intensity"].fillna(0.0)
    return weekly


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def _confidence_label(mape: float) -> str:
    if np.isnan(mape):
        return "low"
    if mape < 0.20:
        return "high"
    if mape < 0.40:
        return "medium"
    return "low"


def _event_intensity_for(future_date: pd.Timestamp, holidays: pd.DataFrame) -> float:
    if holidays is None or holidays.empty:
        return 0.0
    week_end = future_date.to_period("W-MON").end_time.normalize()
    week_start = week_end - pd.Timedelta(days=6)
    sub = holidays[(holidays["date"] >= week_start) & (holidays["date"] <= week_end)]
    if sub.empty:
        return 0.0
    return float(sub["intensite"].max())


@lru_cache(maxsize=128)
def _forecast_inner(store_id: str, product_id: str, now_iso: str, horizon_weeks: int, use_enriched: bool) -> ForecastResult:
    ds = get_store()
    now_ts = pd.Timestamp(now_iso)

    sub = ds.demand[(ds.demand["store_id"] == store_id) & (ds.demand["product_id"] == product_id)]
    sub = sub[sub["date"] <= now_ts][["date", "qty", "promo_share"]].copy()
    weekly = _aggregate_weekly(sub)
    n = len(weekly)
    enrichments = []

    if use_enriched and ds.has_enrichment:
        weekly = _attach_event_intensity(weekly, ds.holidays)
        enrichments.append("holidays_fr")
    else:
        weekly["event_intensity"] = 0.0

    if n < 6:
        avg = float(weekly["qty"].mean()) if n else 0.0
        future_dates = [now_ts + timedelta(weeks=i + 1) for i in range(horizon_weeks)]
        return ForecastResult(
            history=[{"date": str(d.date()), "qty": float(q)} for d, q in zip(weekly["date"], weekly["qty"])],
            forecast=[
                {"date": str(d.date()), "qty_pred": round(avg, 2),
                 "lower": round(max(0, avg * 0.6), 2), "upper": round(avg * 1.4, 2)}
                for d in future_dates
            ],
            mape=float("nan"),
            confidence="low",
            n_train_points=n,
            enrichments_used=enrichments,
        )

    weekly = weekly.copy()
    weekly["lag1"] = weekly["qty"].shift(1)
    weekly["lag2"] = weekly["qty"].shift(2)
    weekly["lag4"] = weekly["qty"].shift(4)
    weekly["month"] = weekly["date"].dt.month
    weekly["weekofyear"] = weekly["date"].dt.isocalendar().week.astype(int)
    feats = ["lag1", "lag2", "lag4", "month", "weekofyear", "promo_share", "event_intensity"]
    train = weekly.dropna(subset=feats)

    if len(train) < 4:
        avg = float(weekly["qty"].mean())
        future_dates = [now_ts + timedelta(weeks=i + 1) for i in range(horizon_weeks)]
        return ForecastResult(
            history=[{"date": str(d.date()), "qty": float(q)} for d, q in zip(weekly["date"], weekly["qty"])],
            forecast=[
                {"date": str(d.date()), "qty_pred": round(avg, 2),
                 "lower": round(max(0, avg * 0.6), 2), "upper": round(avg * 1.4, 2)}
                for d in future_dates
            ],
            mape=float("nan"),
            confidence="low",
            n_train_points=n,
            enrichments_used=enrichments,
        )

    # ---- Bootstrap ensemble ----
    rng = np.random.default_rng(seed=42)
    models = []
    in_sample_preds = []
    n_train = len(train)
    for k in range(K_BOOTSTRAP):
        idx = rng.integers(0, n_train, size=n_train)
        boot = train.iloc[idx]
        m = RandomForestRegressor(
            n_estimators=80, max_depth=6, min_samples_leaf=2,
            random_state=42 + k, n_jobs=-1,
        )
        m.fit(boot[feats], boot["qty"])
        models.append(m)
        in_sample_preds.append(m.predict(train[feats]))
    in_sample_median = np.median(np.array(in_sample_preds), axis=0)
    mape = _mape(train["qty"].values, in_sample_median)
    if K_BOOTSTRAP > 1:
        enrichments.append(f"bootstrap_RF_K={K_BOOTSTRAP}")

    # ---- Forecast iteratif ----
    last = weekly.tail(8).copy()
    promo_avg = float(weekly["promo_share"].tail(8).mean())
    holidays = ds.holidays if (use_enriched and ds.has_enrichment) else None

    future_rows = []
    for _ in range(horizon_weeks):
        next_date = last["date"].iloc[-1] + pd.Timedelta(weeks=1)
        ev_int = _event_intensity_for(next_date, holidays)
        row = {
            "date": next_date,
            "lag1": float(last["qty"].iloc[-1]),
            "lag2": float(last["qty"].iloc[-2]) if len(last) >= 2 else float(last["qty"].iloc[-1]),
            "lag4": float(last["qty"].iloc[-4]) if len(last) >= 4 else float(last["qty"].iloc[-1]),
            "month": int(next_date.month),
            "weekofyear": int(next_date.isocalendar().week),
            "promo_share": promo_avg,
            "event_intensity": ev_int,
        }
        # Predictions des K modeles -> mediane + percentiles
        feat_df = pd.DataFrame([row])[feats]
        preds = np.array([m.predict(feat_df)[0] for m in models])
        pred_med = float(np.median(preds))
        # Booste l'intensite event sur la prediction (effet multiplicatif)
        pred_med = pred_med * (1 + ev_int * 0.3)
        pred_med = max(0.0, pred_med)
        # Intervalle 80%: percentiles 10 et 90 sur le bootstrap, ou residus si K=1
        if K_BOOTSTRAP > 1:
            lower = float(np.percentile(preds, 10)) * (1 + ev_int * 0.3)
            upper = float(np.percentile(preds, 90)) * (1 + ev_int * 0.3)
        else:
            sigma = float(np.std(train["qty"].values - in_sample_median))
            lower = pred_med - 1.28 * sigma
            upper = pred_med + 1.28 * sigma
        row["qty"] = pred_med
        row["lower"] = max(0.0, lower)
        row["upper"] = max(pred_med, upper)
        future_rows.append(row)
        last = pd.concat([last, pd.DataFrame([{k: v for k, v in row.items() if k in last.columns or k == "qty"}])], ignore_index=True)

    history_out = [
        {"date": str(d.date()), "qty": float(q)}
        for d, q in zip(weekly["date"], weekly["qty"])
    ]
    forecast_out = [
        {
            "date": str(r["date"].date()),
            "qty_pred": round(r["qty"], 2),
            "lower": round(r["lower"], 2),
            "upper": round(r["upper"], 2),
        }
        for r in future_rows
    ]

    return ForecastResult(
        history=history_out,
        forecast=forecast_out,
        mape=round(float(mape), 3) if not np.isnan(mape) else float("nan"),
        confidence=_confidence_label(mape),
        n_train_points=int(n),
        enrichments_used=enrichments,
    )


def forecast(store_id: str, product_id: str, now_iso: str, horizon_weeks: int = 4) -> ForecastResult:
    use_enriched = get_settings().use_enriched
    return _forecast_inner(store_id, product_id, now_iso, horizon_weeks, use_enriched)
