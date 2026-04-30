"""Endpoints de reference: stores, products, suppliers, mapping."""
from __future__ import annotations

from fastapi import APIRouter

from ..data.loader import get_store

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/meta")
def meta():
    ds = get_store()
    m = ds.meta
    return {
        "date_min": m["date_min"],
        "date_max": m["date_max"],
        "stock_date_min": m["stock_date_min"],
        "stock_date_max": m["stock_date_max"],
        "stores": m["stores"],
        "products": m["products"],
        "suppliers": m["suppliers"],
        "store_entrepot_mapping": m["store_entrepot_mapping"],
    }
