"""
ETL — harmonise les 5 CSV en 4 artefacts parquet.

Sources (data/raw/):
  - transactions.csv       (10 000 lignes, granularité jour x store x produit)
  - entrepots.csv          (snapshots stock hebdo entrepots/magasins)
  - fournisseurs.csv       (commandes fournisseurs avec delais et conformite)
  - logistique.csv         (livraisons inter-noeuds avec couts et incidents)
  - bilan_commercial.csv   (KPI mensuels par store x produit)

Sorties (data/processed/):
  - demand_daily.parquet      (date, store_id, product_id, qty, revenue, ...)
  - stock_snapshots.parquet   (date, store_id, product_id, stock, seuils, flags)
  - supplier_scores.parquet   (supplier_id, product_id, score, metriques)
  - logistics_lanes.parquet   (depart, arrivee, product_id, duree_moy, cout_moy, incident_rate)
  - bilan_commercial.parquet  (passthrough propre du bilan mensuel)
  - meta.json                 (date min/max, listes stores/produits/fournisseurs, mapping E<->S)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Demand journalière depuis transactions
# ---------------------------------------------------------------------------
def build_demand_daily() -> pd.DataFrame:
    df = pd.read_csv(RAW / "transactions.csv", parse_dates=["date"])
    df = df.rename(columns={"category": "categorie"})

    grp = (
        df.groupby(["date", "store_id", "store_city", "product_id", "product_name", "categorie"], as_index=False)
        .agg(
            qty=("quantity", "sum"),
            revenue=("total_amount", "sum"),
            n_tx=("transaction_id", "count"),
            promo_share=("promotion", lambda s: (s == "Oui").mean()),
            avg_temp=("temperature", "mean"),
            web_visits=("web_visits", "sum"),
        )
    )

    # Exogenous features pour le forecast (1 ligne par jour x store x produit)
    weather_per_day = (
        df.groupby(["date", "store_id"], as_index=False)["weather"]
        .agg(lambda s: s.value_counts().idxmax() if len(s) else "Inconnu")
    )
    special_per_day = (
        df.groupby(["date", "store_id"], as_index=False)["special_day"]
        .agg(lambda s: s.value_counts().idxmax() if len(s) else "Aucun")
    )
    grp = grp.merge(weather_per_day, on=["date", "store_id"], how="left")
    grp = grp.merge(special_per_day, on=["date", "store_id"], how="left")

    grp["dow"] = grp["date"].dt.dayofweek
    grp["month"] = grp["date"].dt.month
    grp["is_weekend"] = grp["dow"].isin([5, 6]).astype(int)
    grp["promo_share"] = grp["promo_share"].fillna(0.0).round(3)
    grp = grp.sort_values(["store_id", "product_id", "date"]).reset_index(drop=True)
    return grp


# ---------------------------------------------------------------------------
# 2. Stock snapshots (entrepôts <-> magasins) avec mapping E<->S
# ---------------------------------------------------------------------------
def build_stock_snapshots() -> pd.DataFrame:
    df = pd.read_csv(RAW / "entrepots.csv", parse_dates=["date_snapshot"])
    df = df.rename(columns={"date_snapshot": "date"})
    df["jours_couverture"] = np.where(
        df["rotation_stock_j"] > 0,
        df["stock_actuel"] / np.maximum(df["stock_actuel"] / df["rotation_stock_j"].replace(0, np.nan), 1),
        np.nan,
    )
    # Couverture = stock / consommation_journalière_estimée. rotation_stock_j est déjà
    # le ratio stock/conso, donc on le réutilise directement (lisible, defensif).
    df["jours_couverture"] = df["rotation_stock_j"]

    # Bornes d'alerte
    df["risque_rupture"] = (df["stock_actuel"] <= df["seuil_min"]).astype(int)
    df["risque_surstock"] = (df["stock_actuel"] >= df["seuil_max"]).astype(int)
    df = df.sort_values(["store_id", "product_id", "date"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 3. Scoring fournisseurs
# ---------------------------------------------------------------------------
def build_supplier_scores() -> pd.DataFrame:
    df = pd.read_csv(RAW / "fournisseurs.csv", parse_dates=["date_commande", "date_livraison"])
    # Discard delais negatifs (regle qualite mentionnee a l'oral)
    df = df[df["delai_reel_j"] >= 0].copy()

    g = (
        df.groupby(["supplier_id", "supplier_name", "pays_origine", "categorie", "product_id", "product_name"], as_index=False)
        .agg(
            n_orders=("order_id", "count"),
            delai_prevu_moy=("delai_prevu_j", "mean"),
            delai_reel_moy=("delai_reel_j", "mean"),
            retard_moy=("retard_j", "mean"),
            taux_fiabilite=("taux_fiabilite", "mean"),
            pct_conforme=("conformite_qualite", lambda s: (s == "Oui").mean()),
            ca_total=("montant_total", "sum"),
        )
    )

    # Score [0..1] : fiabilite x ponctualite x qualite
    ratio_retard = (g["retard_moy"] / g["delai_prevu_moy"]).clip(0, 1).fillna(0)
    g["score"] = (g["taux_fiabilite"] * (1 - ratio_retard) * g["pct_conforme"]).round(3)
    g["delai_prevu_moy"] = g["delai_prevu_moy"].round(1)
    g["delai_reel_moy"] = g["delai_reel_moy"].round(1)
    g["retard_moy"] = g["retard_moy"].round(2)
    g["taux_fiabilite"] = g["taux_fiabilite"].round(3)
    g["pct_conforme"] = g["pct_conforme"].round(3)
    g = g.sort_values("score", ascending=False).reset_index(drop=True)
    return g


# ---------------------------------------------------------------------------
# 4. Logistics lanes
# ---------------------------------------------------------------------------
def build_logistics_lanes() -> pd.DataFrame:
    df = pd.read_csv(RAW / "logistique.csv", parse_dates=["date_depart", "date_arrivee_prevue"])
    g = (
        df.groupby(
            ["entrepot_depart_id", "entrepot_depart_nom", "entrepot_arrivee_id", "entrepot_arrivee_nom",
             "product_id", "product_name", "type_flux"],
            as_index=False,
        )
        .agg(
            n_livraisons=("livraison_id", "count"),
            duree_moy_j=("duree_transport_j", "mean"),
            cout_moy_eur=("cout_transport_eur", "mean"),
            cout_unitaire_moy=("cout_transport_eur", "mean"),  # placeholder, recalcule ci-dessous
            taux_incident=("incident", lambda s: (s != "Aucun").mean()),
            qty_totale=("quantite", "sum"),
        )
    )
    # cout unitaire reel = somme couts / somme quantites
    cu = (
        df.groupby(
            ["entrepot_depart_id", "entrepot_arrivee_id", "product_id", "type_flux"],
            as_index=False,
        )
        .apply(lambda d: pd.Series({"cout_unitaire_moy": d["cout_transport_eur"].sum() / max(d["quantite"].sum(), 1)}))
        .reset_index(drop=True)
    )
    g = g.drop(columns=["cout_unitaire_moy"]).merge(
        cu, on=["entrepot_depart_id", "entrepot_arrivee_id", "product_id", "type_flux"], how="left"
    )
    g["duree_moy_j"] = g["duree_moy_j"].round(2)
    g["cout_moy_eur"] = g["cout_moy_eur"].round(2)
    g["cout_unitaire_moy"] = g["cout_unitaire_moy"].round(3)
    g["taux_incident"] = g["taux_incident"].round(3)
    return g


# ---------------------------------------------------------------------------
# 5. Bilan commercial (passthrough avec date parsee)
# ---------------------------------------------------------------------------
def build_bilan() -> pd.DataFrame:
    df = pd.read_csv(RAW / "bilan_commercial.csv")
    df["periode"] = pd.to_datetime(df["periode"] + "-01")
    return df


# ---------------------------------------------------------------------------
# 6. Meta (mapping E<->S, listes ref)
# ---------------------------------------------------------------------------
def build_meta(demand: pd.DataFrame, stock: pd.DataFrame, suppliers: pd.DataFrame) -> dict:
    # Mapping store_id <-> entrepot_id par ville
    store_city = (
        demand[["store_id", "store_city"]].drop_duplicates().sort_values("store_id")
    )
    ent_city = (
        stock[["entrepot_id", "entrepot_nom", "store_id", "store_city"]]
        .drop_duplicates()
        .sort_values("store_id")
    )
    mapping = ent_city.to_dict(orient="records")

    return {
        "date_min": str(demand["date"].min().date()),
        "date_max": str(demand["date"].max().date()),
        "stock_date_min": str(stock["date"].min().date()),
        "stock_date_max": str(stock["date"].max().date()),
        "stores": store_city.to_dict(orient="records"),
        "store_entrepot_mapping": mapping,
        "products": demand[["product_id", "product_name", "categorie"]]
        .drop_duplicates()
        .sort_values("product_id")
        .to_dict(orient="records"),
        "suppliers": suppliers[["supplier_id", "supplier_name", "pays_origine"]]
        .drop_duplicates()
        .sort_values("supplier_id")
        .to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(">> Building demand_daily...", flush=True)
    demand = build_demand_daily()
    demand.to_parquet(OUT / "demand_daily.parquet", index=False)
    print(f"   {len(demand):>6} rows  ({demand['date'].min().date()} -> {demand['date'].max().date()})")

    print(">> Building stock_snapshots...", flush=True)
    stock = build_stock_snapshots()
    stock.to_parquet(OUT / "stock_snapshots.parquet", index=False)
    print(f"   {len(stock):>6} rows  ({stock['date'].nunique()} snapshot dates)")

    print(">> Building supplier_scores...", flush=True)
    suppliers = build_supplier_scores()
    suppliers.to_parquet(OUT / "supplier_scores.parquet", index=False)
    print(f"   {len(suppliers):>6} (supplier x product) pairs")

    print(">> Building logistics_lanes...", flush=True)
    lanes = build_logistics_lanes()
    lanes.to_parquet(OUT / "logistics_lanes.parquet", index=False)
    print(f"   {len(lanes):>6} lanes")

    print(">> Building bilan_commercial...", flush=True)
    bilan = build_bilan()
    bilan.to_parquet(OUT / "bilan_commercial.parquet", index=False)
    print(f"   {len(bilan):>6} rows")

    print(">> Building meta.json...", flush=True)
    meta = build_meta(demand, stock, suppliers)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(f"   stores={len(meta['stores'])}, products={len(meta['products'])}, suppliers={len(meta['suppliers'])}")

    print("\nOK -> data/processed/ contient", len(list(OUT.iterdir())), "fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
