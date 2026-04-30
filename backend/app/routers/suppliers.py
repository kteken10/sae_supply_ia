"""Endpoints fournisseurs (scoring + detail)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..data.loader import get_store

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("")
def list_suppliers():
    ds = get_store()
    df = ds.suppliers.sort_values("score", ascending=False)
    return {
        "suppliers": df.to_dict(orient="records"),
        "count": len(df),
    }


@router.get("/{supplier_id}")
def supplier_detail(supplier_id: str):
    ds = get_store()
    sub = ds.suppliers[ds.suppliers["supplier_id"] == supplier_id]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Fournisseur inconnu")
    row = sub.iloc[0]
    out = {
        "supplier_id": row["supplier_id"],
        "supplier_name": row["supplier_name"],
        "pays_origine": row["pays_origine"],
        "categorie": row["categorie"],
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "score": float(row["score"]),
        "n_orders": int(row["n_orders"]),
        "delai_prevu_moy": float(row["delai_prevu_moy"]),
        "delai_reel_moy": float(row["delai_reel_moy"]),
        "retard_moy": float(row["retard_moy"]),
        "taux_fiabilite": float(row["taux_fiabilite"]),
        "pct_conforme": float(row["pct_conforme"]),
        "ca_total": float(row["ca_total"]),
        "is_synthetic": bool(row.get("is_synthetic", False)) if "is_synthetic" in sub.columns else False,
    }
    if "tier" in sub.columns:
        out["tier"] = str(row["tier"])
    return out
