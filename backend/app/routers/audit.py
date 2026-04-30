"""Endpoint audit / tracabilite IA Act."""
from __future__ import annotations

from fastapi import APIRouter, Query

from .. import audit as audit_log
from ..data.loader import get_store
from ..settings import get_settings

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_events(limit: int = Query(100, ge=1, le=1000)):
    events = audit_log.read_events(limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/model-card")
def model_card():
    """Documentation du modele pour conformite IA Act."""
    ds = get_store()
    settings = get_settings()
    n_real_suppliers = len(ds.suppliers_real) if not ds.suppliers_real.empty else 0
    n_synthetic_suppliers = (
        int(ds.suppliers_enriched["is_synthetic"].sum())
        if ds.has_enrichment
        else 0
    )

    return {
        "name": "SAE Carrefour - Forecast & Recommandation",
        "version": "0.2.0-mvp-enriched",
        "type": "RandomForestRegressor (sklearn) + bootstrap K=10",
        "purpose": "Anticiper la demande et recommander des actions de reassort sur SKU x magasin.",
        "training_data": {
            "source_principale": "transactions 2025 (10 000 lignes), stocks hebdo, fournisseurs, logistique",
            "date_range": "2025-01-01 -> 2026-01-01",
            "granularite": "hebdomadaire (W-MON)",
            "scope": f"8 magasins x 10 produits x {n_real_suppliers + n_synthetic_suppliers} fournisseurs",
        },
        "features": [
            "lag_1", "lag_2", "lag_4",
            "month", "weekofyear",
            "promo_share",
            "event_intensity (si enrichissement actif)",
        ],
        "hyperparams": {
            "n_estimators": 80, "max_depth": 6, "min_samples_leaf": 2,
            "K_bootstrap": 10,
        },
        "metriques": {
            "MAPE": "calcule par paire (store, product), retourne avec chaque forecast",
            "intervalle_80%": "percentiles 10/90 sur les K modeles bootstrap",
        },
        "limites_assumees": [
            "Donnees figees (jeu d'entrainement 2025), pas de flux live",
            "1 an d'historique seulement (2-3 ans seraient ideaux)",
            "Couverture journaliere sparse (~106 obs / 365 j) -> agregation hebdo",
            "Pas d'elasticite prix mesuree",
            "Pas de cannibalisation inter-produits",
            "Ruptures cote client (demande perdue) non observees",
        ],
        "supervision_humaine": {
            "principe": "Toute recommandation doit etre validee par un operateur via /api/recommendations/validate avant execution",
            "log_audit": "audit_log.jsonl (append-only, JSON par decision)",
        },
        "ia_act": {
            "categorie": "haut risque (gestion stock activite critique)",
            "obligations_couvertes": [
                "tracabilite des decisions (audit log)",
                "documentation technique (cette model card)",
                "supervision humaine (validation explicite)",
                "transparence (metriques + enrichissements retournes a chaque appel)",
                "auditabilite des donnees synthetiques (flag is_synthetic + log toggle)",
            ],
        },
        "enrichissements": {
            "actif": settings.use_enriched and ds.has_enrichment,
            "disponible": ds.has_enrichment,
            "details": [
                {
                    "nom": "multi_suppliers",
                    "type": "synthetique",
                    "description": f"{n_synthetic_suppliers} fournisseurs challengers generes (3 par produit : Premium / Standard / Discount)",
                    "methode": "perturbation aleatoire des stats de l'incumbent (delai +/- 30%, fiabilite +/- 0.1, conformite +/- 0.1) avec profils tier-specific",
                    "motivation": "Le dataset original a 1 seul fournisseur par produit, rendant la 'selection automatique' triviale. Les challengers permettent de demontrer la logique prescriptive de choix.",
                    "flag": "champ is_synthetic=True dans suppliers_enriched.parquet",
                },
                {
                    "nom": "holidays_fr",
                    "type": "donnee externe (lib python `holidays`)",
                    "description": "Calendrier reel des jours feries FR + Black Friday + Soldes hiver/ete + periode Noel, avec intensite commerciale",
                    "methode": "API holidays.France() + regles deterministes pour les temps forts retail",
                    "motivation": "Les `special_day` du dataset original sont mal places (Black Friday en janvier, etc.). La feature event_intensity du modele exploite ce calendrier corrige.",
                    "flag": "donnee deterministe non synthetique",
                },
                {
                    "nom": "supplier_capacity",
                    "type": "synthetique calibre",
                    "description": "Capacite mensuelle par fournisseur, calibree sur le volume reel des commandes 2025 + saisonnalite (aout -40%, nov-dec +30%)",
                    "methode": "loi log-normale autour du volume mensuel moyen historique",
                    "motivation": "Permet de detecter quand une recommandation depasse la capacite du fournisseur et propose un fallback.",
                    "flag": "is_synthetic=True dans supplier_capacity.parquet",
                },
                {
                    "nom": "category_storage_costs",
                    "type": "prior metier",
                    "description": "Cout de stockage en eur/unite/jour par categorie (Alimentaire 0.05 / Droguerie 0.02 / Textile 0.01 / Electronique 0.04)",
                    "methode": "table fixe basee sur des priors retail standard",
                    "motivation": "Permet de chiffrer en eur le cout de chaque rupture/surstock, pour arbitrer en valeur et pas seulement en quantite.",
                    "flag": "table de reference deterministe",
                },
                {
                    "nom": "climate_norms",
                    "type": "donnee externe (Meteo France approximee)",
                    "description": "Temperature moyenne et type de temps dominant par ville x mois",
                    "methode": "moyennes climatiques 1991-2020 approximees + distribution conditionnelle de meteo par mois",
                    "motivation": "La meteo du dataset transactions est aleatoire et non spatialement coherente. Pas encore branche sur le forecast.",
                    "flag": "donnee externe deterministe",
                },
                {
                    "nom": "bootstrap_RF",
                    "type": "technique ML",
                    "description": "K=10 RandomForest entraines sur reechantillonnages bootstrap, prediction = mediane, intervalle 80% = percentiles 10/90",
                    "methode": "bagging classique",
                    "motivation": "Reduit la variance de la prediction et fournit un intervalle de confiance plus robuste qu'un seul RF.",
                    "flag": "technique deterministe avec seed",
                },
            ],
        },
    }
