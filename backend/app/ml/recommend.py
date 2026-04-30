"""
Moteur de recommandation prescriptif.

Pour chaque (store, product) a risque, calcule:
  - quantite a commander = forecast(N semaines) + seuil_min - stock_actuel
  - meilleur fournisseur (top score) parmi tous les candidats du produit
  - alternative (n.2) pour comparer
  - check capacite mensuelle du fournisseur
  - meilleure lane logistique (cout unitaire min sur taux_incident < 0.2)
  - cout de stockage estime sur la duree de couverture
  - urgence (jours avant rupture)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import pandas as pd

from ..data.loader import get_store
from ..settings import get_settings
from .forecast import forecast as run_forecast


@dataclass
class Recommendation:
    store_id: str
    store_city: str
    product_id: str
    product_name: str
    categorie: str
    stock_actuel: int
    seuil_min: int
    jours_avant_rupture: float
    urgence: str
    qty_recommandee: int
    forecast_qty_4w: float
    confidence: str
    fournisseur: dict | None
    fournisseur_alt: dict | None
    capacity_warning: str | None
    lane: dict | None
    cout_stockage_evite: float | None
    raison: str
    enrichments_used: list = field(default_factory=list)
    generated_at: str = ""


def _urgency(jours: float) -> str:
    if jours < 2:
        return "critical"
    if jours < 5:
        return "high"
    if jours < 10:
        return "medium"
    return "low"


def _supplier_candidates(suppliers: pd.DataFrame, product_id: str) -> pd.DataFrame:
    sub = suppliers[suppliers["product_id"] == product_id].sort_values("score", ascending=False)
    return sub


def _supplier_to_dict(row: pd.Series) -> dict:
    d = {
        "supplier_id": row["supplier_id"],
        "supplier_name": row["supplier_name"],
        "pays_origine": row["pays_origine"],
        "score": float(row["score"]),
        "delai_prevu_moy": float(row["delai_prevu_moy"]),
        "retard_moy": float(row["retard_moy"]),
        "pct_conforme": float(row["pct_conforme"]),
        "is_synthetic": bool(row.get("is_synthetic", False)),
    }
    if "tier" in row:
        d["tier"] = str(row["tier"])
    return d


def _pick_lane(lanes: pd.DataFrame, entrepot_id: str, product_id: str) -> Optional[dict]:
    sub = lanes[
        (lanes["entrepot_arrivee_id"] == entrepot_id)
        & (lanes["product_id"] == product_id)
        & (lanes["taux_incident"] < 0.2)
    ].copy()
    if sub.empty:
        sub = lanes[(lanes["entrepot_arrivee_id"] == entrepot_id) & (lanes["product_id"] == product_id)]
    if sub.empty:
        return None
    row = sub.sort_values("cout_unitaire_moy").iloc[0]
    return {
        "from": row["entrepot_depart_nom"],
        "to": row["entrepot_arrivee_nom"],
        "type_flux": row["type_flux"],
        "duree_moy_j": float(row["duree_moy_j"]),
        "cout_unitaire_moy": float(row["cout_unitaire_moy"]),
        "taux_incident": float(row["taux_incident"]),
    }


def recommend_one(store_id: str, product_id: str, now: date, horizon_weeks: int = 4) -> Optional[Recommendation]:
    ds = get_store()
    latest = ds.latest_stock_at(now)
    row = latest[(latest["store_id"] == store_id) & (latest["product_id"] == product_id)]
    if row.empty:
        return None
    s = row.iloc[0]

    fc = run_forecast(store_id, product_id, str(now), horizon_weeks)
    forecast_qty = sum(p["qty_pred"] for p in fc.forecast)
    daily_avg = forecast_qty / max(horizon_weeks * 7, 1)

    stock_actuel = int(s["stock_actuel"])
    seuil_min = int(s["seuil_min"])
    jours = stock_actuel / max(daily_avg, 0.01)

    qty_reco = max(0, int(round(forecast_qty + seuil_min - stock_actuel)))

    # ---- Fournisseur principal + alternative
    candidates = _supplier_candidates(ds.suppliers, product_id)
    fournisseur = _supplier_to_dict(candidates.iloc[0]) if not candidates.empty else None
    fournisseur_alt = (
        _supplier_to_dict(candidates.iloc[1])
        if len(candidates) >= 2
        else None
    )

    enriched_active = ds.has_enrichment and get_settings().use_enriched

    # ---- Verif capacite mensuelle
    capacity_warning = None
    if fournisseur and enriched_active:
        cap = ds.supplier_capacity_for(
            fournisseur["supplier_id"], product_id, pd.Timestamp(now).month
        )
        if cap is not None and qty_reco > cap:
            capacity_warning = (
                f"Quantite reco ({qty_reco}) > capacite mensuelle "
                f"de {fournisseur['supplier_name']} ({cap}). Splitter ou solliciter "
                f"{fournisseur_alt['supplier_name']}." if fournisseur_alt
                else f"Quantite reco ({qty_reco}) > capacite mensuelle ({cap})."
            )

    # ---- Lane logistique
    entrepot_id = ds.store_to_entrepot.get(store_id)
    lane = _pick_lane(ds.lanes, entrepot_id, product_id) if entrepot_id else None

    # ---- Cout stockage evite (estimation)
    cout_stockage = ds.storage_cost(s["categorie"]) if enriched_active else None
    cout_stockage_evite = None
    if cout_stockage is not None and jours < 999:
        # Si on ne commande PAS : rupture dans `jours`. Cout d'opportunite =
        # qty_reco x cout_stockage x 7 (1 semaine de surcout d'urgence).
        cout_stockage_evite = round(qty_reco * cout_stockage * 7, 2)

    # ---- Raison
    raison_parts = []
    if stock_actuel <= seuil_min:
        raison_parts.append(f"stock={stock_actuel} <= seuil_min={seuil_min}")
    if jours < 5:
        raison_parts.append(f"couverture {jours:.1f}j < 5j")
    if not raison_parts:
        raison_parts.append("anticipation horizon 4 semaines")
    raison = " ; ".join(raison_parts)

    # ---- Tracage enrichissements utilises
    enrichments = []
    if enriched_active:
        if fournisseur and fournisseur.get("is_synthetic"):
            enrichments.append("multi-suppliers (synthetic challengers)")
        if fournisseur and ds.supplier_capacity_for(
            fournisseur["supplier_id"], product_id, pd.Timestamp(now).month
        ) is not None:
            enrichments.append("supplier_capacity")
        if cout_stockage_evite is not None:
            enrichments.append("category_storage_costs")
        enrichments.extend(fc.enrichments_used)

    return Recommendation(
        store_id=store_id,
        store_city=s["store_city"],
        product_id=product_id,
        product_name=s["product_name"],
        categorie=s["categorie"],
        stock_actuel=stock_actuel,
        seuil_min=seuil_min,
        jours_avant_rupture=round(jours, 1),
        urgence=_urgency(jours),
        qty_recommandee=qty_reco,
        forecast_qty_4w=round(forecast_qty, 1),
        confidence=fc.confidence,
        fournisseur=fournisseur,
        fournisseur_alt=fournisseur_alt,
        capacity_warning=capacity_warning,
        lane=lane,
        cout_stockage_evite=cout_stockage_evite,
        raison=raison,
        enrichments_used=enrichments,
        generated_at=str(now),
    )


def recommend_at_risk(now: date, max_items: int = 50) -> List[Recommendation]:
    ds = get_store()
    latest = ds.latest_stock_at(now)
    if latest.empty:
        return []

    at_risk = latest[
        (latest["risque_rupture"] == 1) | (latest["jours_couverture_reel"] < 5)
    ].copy()
    at_risk = at_risk.sort_values("jours_couverture_reel", ascending=True).head(max_items)

    results: List[Recommendation] = []
    for _, r in at_risk.iterrows():
        rec = recommend_one(r["store_id"], r["product_id"], now)
        if rec:
            results.append(rec)
    return results
