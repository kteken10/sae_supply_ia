"""Endpoints recommandations + validation humaine."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .. import audit
from ..config import parse_date
from ..ml.recommend import recommend_at_risk, recommend_one

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def list_recommendations(now: str | None = Query(None), max_items: int = 30):
    now_d = parse_date(now)
    recs = recommend_at_risk(now_d, max_items=max_items)
    return {
        "now": str(now_d),
        "recommendations": [asdict(r) for r in recs],
        "count": len(recs),
    }


@router.get("/one")
def single(store_id: str, product_id: str, now: str | None = Query(None)):
    now_d = parse_date(now)
    rec = recommend_one(store_id, product_id, now_d)
    if rec is None:
        raise HTTPException(status_code=404, detail="Pas de stock pour cette paire (store, product) a la date demandee.")
    return asdict(rec)


class ValidationPayload(BaseModel):
    store_id: str
    product_id: str
    qty_recommandee: int
    fournisseur_id: str | None = None
    decision: str  # "validated" / "rejected" / "modified"
    qty_modified: int | None = None
    user: str = "anonymous"
    note: str | None = None


@router.post("/validate")
def validate(payload: ValidationPayload):
    record = audit.append_event(
        "recommendation_decision",
        payload.model_dump(),
    )
    return {"ok": True, "record": record}
