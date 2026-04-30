"""Point d'entree FastAPI."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .data.loader import get_store
from .routers import audit, catalog, forecast, kpis, recommendations, settings as settings_router, stock, suppliers

app = FastAPI(
    title="SAE Carrefour - Analyse Prescriptive",
    version="0.1.0",
    description="Backend MVP - forecast, recommandations et tracabilite IA Act.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _warmup():
    # Pre-charge les parquets au boot pour eviter le cold start sur la 1ere requete.
    get_store()


@app.get("/api/health")
def health():
    ds = get_store()
    return {
        "status": "ok",
        "rows": {
            "demand": len(ds.demand),
            "stock": len(ds.stock),
            "suppliers": len(ds.suppliers),
            "lanes": len(ds.lanes),
            "bilan": len(ds.bilan),
        },
    }


app.include_router(catalog.router)
app.include_router(kpis.router)
app.include_router(stock.router)
app.include_router(forecast.router)
app.include_router(recommendations.router)
app.include_router(suppliers.router)
app.include_router(audit.router)
app.include_router(settings_router.router)
