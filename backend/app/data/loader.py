"""Charge les parquets une fois au boot et expose un DataStore."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import PROCESSED
from ..settings import get_settings


@dataclass
class DataStore:
    demand: pd.DataFrame = field(default_factory=pd.DataFrame)
    stock: pd.DataFrame = field(default_factory=pd.DataFrame)
    suppliers_real: pd.DataFrame = field(default_factory=pd.DataFrame)
    suppliers_enriched: pd.DataFrame = field(default_factory=pd.DataFrame)
    capacity: pd.DataFrame = field(default_factory=pd.DataFrame)
    holidays: pd.DataFrame = field(default_factory=pd.DataFrame)
    climate: pd.DataFrame = field(default_factory=pd.DataFrame)
    category_costs: pd.DataFrame = field(default_factory=pd.DataFrame)
    lanes: pd.DataFrame = field(default_factory=pd.DataFrame)
    bilan: pd.DataFrame = field(default_factory=pd.DataFrame)
    meta: dict = field(default_factory=dict)
    store_to_entrepot: dict = field(default_factory=dict)
    has_enrichment: bool = False

    @classmethod
    def load(cls) -> "DataStore":
        ds = cls()
        ds.demand = pd.read_parquet(PROCESSED / "demand_daily.parquet")
        ds.demand["date"] = pd.to_datetime(ds.demand["date"]).dt.tz_localize(None)
        ds.stock = pd.read_parquet(PROCESSED / "stock_snapshots.parquet")
        ds.stock["date"] = pd.to_datetime(ds.stock["date"]).dt.tz_localize(None)
        ds.suppliers_real = pd.read_parquet(PROCESSED / "supplier_scores.parquet")
        ds.lanes = pd.read_parquet(PROCESSED / "logistics_lanes.parquet")
        ds.bilan = pd.read_parquet(PROCESSED / "bilan_commercial.parquet")
        ds.meta = json.loads((PROCESSED / "meta.json").read_text(encoding="utf-8"))
        ds.store_to_entrepot = {
            row["store_id"]: row["entrepot_id"] for row in ds.meta["store_entrepot_mapping"]
        }

        # Enrichissements (optionnels, on les charge tous si presents)
        enriched_path = PROCESSED / "suppliers_enriched.parquet"
        if enriched_path.exists():
            ds.suppliers_enriched = pd.read_parquet(enriched_path)
            ds.capacity = pd.read_parquet(PROCESSED / "supplier_capacity.parquet")
            ds.holidays = pd.read_parquet(PROCESSED / "holidays_fr.parquet")
            ds.holidays["date"] = pd.to_datetime(ds.holidays["date"]).dt.tz_localize(None)
            ds.climate = pd.read_parquet(PROCESSED / "climate_norms.parquet")
            ds.category_costs = pd.read_parquet(PROCESSED / "category_costs.parquet")
            ds.has_enrichment = True
        return ds

    @property
    def suppliers(self) -> pd.DataFrame:
        """Retourne le dataset fournisseurs actif selon le toggle d'enrichissement."""
        if get_settings().use_enriched and self.has_enrichment:
            return self.suppliers_enriched
        return self.suppliers_real

    def storage_cost(self, categorie: str) -> float | None:
        if self.category_costs.empty:
            return None
        row = self.category_costs[self.category_costs["categorie"] == categorie]
        if row.empty:
            return None
        return float(row.iloc[0]["cout_stockage_jour"])

    def supplier_capacity_for(self, supplier_id: str, product_id: str, month: int) -> int | None:
        if self.capacity.empty:
            return None
        row = self.capacity[
            (self.capacity["supplier_id"] == supplier_id)
            & (self.capacity["product_id"] == product_id)
            & (self.capacity["month"] == month)
        ]
        if row.empty:
            return None
        return int(row.iloc[0]["capacity_units"])

    def event_for(self, d: pd.Timestamp) -> tuple[str, float]:
        """Retourne (evenement, intensite) pour une date donnee."""
        if self.holidays.empty:
            return ("Aucun", 0.0)
        row = self.holidays[self.holidays["date"] == pd.Timestamp(d).normalize()]
        if row.empty:
            return ("Aucun", 0.0)
        return (str(row.iloc[0]["evenement"]), float(row.iloc[0]["intensite"]))

    def latest_stock_at(self, now_date) -> pd.DataFrame:
        """Snapshot de stock le plus recent <= now_date, enrichi d'une couverture
        recalculee depuis la demande observee."""
        ts = pd.Timestamp(now_date)
        df = self.stock[self.stock["date"] <= ts]
        if df.empty:
            return df
        latest = df.groupby(["store_id", "product_id"])["date"].max().reset_index()
        snap = df.merge(latest, on=["store_id", "product_id", "date"])

        demand_window = self.demand[
            (self.demand["date"] <= ts)
            & (self.demand["date"] > ts - pd.Timedelta(days=28))
        ]
        avg_daily = (
            demand_window.groupby(["store_id", "product_id"])["qty"].sum() / 28.0
        ).rename("demand_daily_avg").reset_index()
        snap = snap.merge(avg_daily, on=["store_id", "product_id"], how="left")
        snap["demand_daily_avg"] = snap["demand_daily_avg"].fillna(0.0)
        snap["jours_couverture_reel"] = (
            snap["stock_actuel"] / snap["demand_daily_avg"].replace(0, pd.NA)
        ).fillna(999).clip(upper=999).astype(float).round(1)
        return snap


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore.load()
    return _store
