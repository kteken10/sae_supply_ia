"""
Enrichissements synthetiques pour pallier les angles morts du dataset.

Chaque artefact produit est :
  - place dans data/processed/
  - flagge `is_synthetic=True` quand applicable
  - documente dans la model card (/api/audit/model-card)

Sorties :
  - suppliers_enriched.parquet : 10 reels + ~30 synthetiques (3-4 par produit)
  - holidays_fr.parquet         : calendrier evenements 2025-2026 par date
  - supplier_capacity.parquet   : capacite mensuelle par fournisseur
  - category_costs.parquet      : cout de stockage par categorie
  - climate_norms.parquet       : meteo + temperature attendues par ville x mois
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Multi-fournisseurs
# ---------------------------------------------------------------------------
def build_suppliers_enriched() -> pd.DataFrame:
    """3 challengers synthetiques par produit, calibres autour du fournisseur reel."""
    real = pd.read_parquet(PROCESSED / "supplier_scores.parquet")
    real = real.assign(is_synthetic=False)

    rng = np.random.default_rng(seed=42)
    pays_pool = {
        "Premium": ["France", "Allemagne", "Pays-Bas", "Belgique", "Italie"],
        "Standard": ["Espagne", "Pologne", "Portugal", "Tchequie", "Roumanie"],
        "Discount": ["Chine", "Inde", "Vietnam", "Bangladesh", "Turquie"],
    }
    name_templates = {
        "Premium": ["{cat}Excellence", "Euro{cat}Premium", "Top{cat}Direct"],
        "Standard": ["{cat}Trade", "Mid{cat}Co", "{cat}Network"],
        "Discount": ["{cat}LowCost", "Asia{cat}Bulk", "Global{cat}Source"],
    }

    rows = []
    next_id = 11
    for _, src in real.iterrows():
        for tier in ["Premium", "Standard", "Discount"]:
            sid = f"F{next_id:03d}"
            next_id += 1
            cat_short = src["categorie"][:4]
            name = rng.choice(name_templates[tier]).format(cat=cat_short)
            pays = rng.choice(pays_pool[tier])

            # Profils tier-specific
            if tier == "Premium":
                delai = src["delai_prevu_moy"] * rng.uniform(0.7, 0.9)
                retard = src["retard_moy"] * rng.uniform(0.3, 0.6)
                fiab = min(0.99, src["taux_fiabilite"] + rng.uniform(0.05, 0.1))
                conf = min(0.99, src["pct_conforme"] + rng.uniform(0.03, 0.07))
                ca_factor = rng.uniform(0.3, 0.6)  # plus petit volume
            elif tier == "Standard":
                delai = src["delai_prevu_moy"] * rng.uniform(0.95, 1.1)
                retard = src["retard_moy"] * rng.uniform(0.8, 1.2)
                fiab = max(0.6, src["taux_fiabilite"] + rng.uniform(-0.05, 0.05))
                conf = max(0.7, src["pct_conforme"] + rng.uniform(-0.05, 0.05))
                ca_factor = rng.uniform(0.5, 0.9)
            else:  # Discount
                delai = src["delai_prevu_moy"] * rng.uniform(1.2, 1.6)
                retard = src["retard_moy"] * rng.uniform(1.4, 2.0)
                fiab = max(0.55, src["taux_fiabilite"] - rng.uniform(0.1, 0.2))
                conf = max(0.6, src["pct_conforme"] - rng.uniform(0.1, 0.2))
                ca_factor = rng.uniform(0.7, 1.1)  # gros volumes mais qualite moindre

            ratio_retard = max(0, min(1, retard / max(delai, 0.1)))
            score = round(fiab * (1 - ratio_retard) * conf, 3)

            rows.append({
                "supplier_id": sid,
                "supplier_name": f"{name} {tier[0]}",
                "pays_origine": pays,
                "categorie": src["categorie"],
                "product_id": src["product_id"],
                "product_name": src["product_name"],
                "n_orders": int(src["n_orders"] * ca_factor * rng.uniform(0.7, 1.3)),
                "delai_prevu_moy": round(delai, 1),
                "delai_reel_moy": round(delai + retard, 1),
                "retard_moy": round(retard, 2),
                "taux_fiabilite": round(fiab, 3),
                "pct_conforme": round(conf, 3),
                "ca_total": round(src["ca_total"] * ca_factor, 2),
                "score": score,
                "tier": tier,
                "is_synthetic": True,
            })

    real["tier"] = "Incumbent"
    enriched = pd.concat([real, pd.DataFrame(rows)], ignore_index=True)
    enriched = enriched.sort_values(["product_id", "score"], ascending=[True, False]).reset_index(drop=True)
    return enriched


# ---------------------------------------------------------------------------
# 2. Calendrier des evenements (jours feries FR + temps forts retail)
# ---------------------------------------------------------------------------
def build_holidays() -> pd.DataFrame:
    """Calendrier 2025-2026 par date avec evenement type + intensite commerciale."""
    try:
        import holidays
        fr = holidays.France(years=[2025, 2026])
    except Exception:
        fr = {}

    rows = []
    # Generer toutes les dates 2025-2026
    rng_dates = pd.date_range("2025-01-01", "2026-01-15", freq="D")
    for d in rng_dates:
        evenement = "Aucun"
        intensite = 0.0  # multiplicateur sur la demande nominale

        # Jours feries officiels
        if d.date() in fr:
            evenement = fr.get(d.date())
            intensite = 0.3 if "1er" in evenement or "Noel" in evenement.lower() else 0.1

        # Soldes hiver : 8 janv -> 4 fev
        if (d.month == 1 and d.day >= 8) or (d.month == 2 and d.day <= 4):
            evenement = "Soldes hiver"
            intensite = 0.5

        # Soldes ete : derniere semaine juin -> derniere semaine juillet
        elif (d.month == 6 and d.day >= 25) or (d.month == 7 and d.day <= 22):
            evenement = "Soldes ete"
            intensite = 0.5

        # Black Friday : dernier vendredi de novembre + week-end
        elif d.month == 11 and d.weekday() == 4 and d.day >= 23:
            evenement = "Black Friday"
            intensite = 1.2
        elif d.month == 11 and d.day >= 23 and d.weekday() in [5, 6]:
            evenement = "Black Weekend"
            intensite = 0.8

        # Cyber Monday
        elif d.month == 11 and d.weekday() == 0 and d.day >= 27:
            evenement = "Cyber Monday"
            intensite = 0.6

        # Periode Noel : 1er dec -> 24 dec
        elif d.month == 12 and d.day <= 24:
            evenement = "Periode Noel"
            intensite = 0.6 + (d.day / 24) * 0.4  # monte vers Noel

        rows.append({"date": d, "evenement": evenement, "intensite": round(intensite, 2)})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Capacite mensuelle fournisseur
# ---------------------------------------------------------------------------
def build_supplier_capacity(suppliers_enriched: pd.DataFrame) -> pd.DataFrame:
    """Capacite mensuelle calibree sur le volume reel commande historiquement.

    On reprend le CSV brut pour avoir la quantite totale annuelle par fournisseur
    (n_orders est juste un compte, pas un volume). Pour les synthetiques, on
    extrapole depuis le ca_total et un prix moyen par categorie.
    """
    rng = np.random.default_rng(seed=43)
    raw = pd.read_csv(ROOT / "data" / "raw" / "fournisseurs.csv")
    qty_real = raw.groupby("supplier_id")["quantite_commandee"].sum().to_dict()
    avg_unit_qty = raw.groupby("supplier_id")["quantite_commandee"].mean().to_dict()

    rows = []
    for _, s in suppliers_enriched.iterrows():
        if s["supplier_id"] in qty_real:
            yearly_qty = qty_real[s["supplier_id"]]
        else:
            # Synthetique : on derive depuis n_orders x quantite moyenne du tier
            mean_qty = float(np.mean(list(avg_unit_qty.values())))
            yearly_qty = s["n_orders"] * mean_qty * rng.uniform(0.7, 1.3)

        base = yearly_qty / 12
        for month in range(1, 13):
            cap = int(base * 1.4 * rng.lognormal(mean=0, sigma=0.15))  # 40% de marge sur historique
            if month == 8:
                cap = int(cap * 0.6)  # vacances
            elif month in [11, 12]:
                cap = int(cap * 1.3)  # peak holiday
            rows.append({
                "supplier_id": s["supplier_id"],
                "product_id": s["product_id"],
                "month": month,
                "capacity_units": max(cap, 50),
                "is_synthetic": True,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Cout de stockage par categorie
# ---------------------------------------------------------------------------
def build_category_costs() -> pd.DataFrame:
    """Cout de stockage standard par categorie (eur/unite/jour)."""
    return pd.DataFrame([
        {"categorie": "Alimentaire", "cout_stockage_jour": 0.05, "raison": "frais, rotation rapide, refrigeration"},
        {"categorie": "Droguerie", "cout_stockage_jour": 0.02, "raison": "produits stables"},
        {"categorie": "Textile", "cout_stockage_jour": 0.01, "raison": "encombrement modere, durable"},
        {"categorie": "Electronique", "cout_stockage_jour": 0.04, "raison": "valeur unitaire haute, securite, assurance"},
    ])


# ---------------------------------------------------------------------------
# 5. Normes climatiques par ville x mois
# ---------------------------------------------------------------------------
def build_climate_norms() -> pd.DataFrame:
    """Temperature et type de temps dominants par (ville, mois) - normes Meteo France approx."""
    # Source : moyennes climatiques 1991-2020, valeurs approximatives
    # T moyenne par mois pour chaque ville
    profiles = {
        "Paris":     [4, 5, 8, 11, 15, 18, 20, 20, 17, 13, 8, 5],
        "Lyon":      [3, 4, 8, 11, 15, 19, 22, 21, 18, 13, 7, 4],
        "Marseille": [7, 8, 11, 14, 18, 22, 25, 24, 21, 16, 11, 8],
        "Nice":      [9, 9, 12, 14, 18, 21, 24, 24, 21, 17, 13, 10],
        "Lille":     [3, 4, 7, 10, 14, 17, 19, 19, 16, 12, 7, 4],
        "Toulouse":  [6, 7, 11, 13, 17, 21, 23, 23, 20, 15, 10, 7],
        "Bordeaux":  [6, 7, 10, 13, 16, 20, 22, 22, 19, 15, 10, 7],
        "Nantes":    [5, 6, 9, 11, 15, 18, 20, 20, 17, 13, 8, 5],
    }
    weather_dist = {
        # (sun, cloud, rain, snow) probabilities per month
        1:  (0.20, 0.40, 0.30, 0.10),
        2:  (0.25, 0.40, 0.30, 0.05),
        3:  (0.35, 0.35, 0.30, 0.00),
        4:  (0.40, 0.30, 0.30, 0.00),
        5:  (0.50, 0.25, 0.25, 0.00),
        6:  (0.60, 0.20, 0.20, 0.00),
        7:  (0.65, 0.20, 0.15, 0.00),
        8:  (0.65, 0.20, 0.15, 0.00),
        9:  (0.50, 0.25, 0.25, 0.00),
        10: (0.35, 0.30, 0.35, 0.00),
        11: (0.20, 0.40, 0.40, 0.00),
        12: (0.20, 0.35, 0.35, 0.10),
    }
    rows = []
    for city, temps in profiles.items():
        for month in range(1, 13):
            t = temps[month - 1]
            sun, cloud, rain, snow = weather_dist[month]
            # weather dominant
            dominant = max(
                [("Soleil", sun), ("Nuageux", cloud), ("Pluie", rain), ("Neige", snow)],
                key=lambda x: x[1],
            )[0]
            # Mediterraneens : moins de pluie ete
            if city in ["Marseille", "Nice"] and month in [6, 7, 8]:
                dominant = "Soleil"
            # Lille : plus de pluie/nuage
            if city == "Lille" and month in [10, 11, 12, 1, 2]:
                dominant = "Pluie"

            rows.append({
                "store_city": city, "month": month,
                "temp_norm": t, "weather_dominant": dominant,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(">> Building suppliers_enriched...", flush=True)
    suppliers = build_suppliers_enriched()
    suppliers.to_parquet(PROCESSED / "suppliers_enriched.parquet", index=False)
    print(f"   {len(suppliers):>4} fournisseurs ({(suppliers['is_synthetic']).sum()} synthetiques)")

    print(">> Building holidays_fr...", flush=True)
    hol = build_holidays()
    hol.to_parquet(PROCESSED / "holidays_fr.parquet", index=False)
    n_events = (hol["evenement"] != "Aucun").sum()
    print(f"   {len(hol):>4} dates ({n_events} avec evenement)")

    print(">> Building supplier_capacity...", flush=True)
    cap = build_supplier_capacity(suppliers)
    cap.to_parquet(PROCESSED / "supplier_capacity.parquet", index=False)
    print(f"   {len(cap):>4} (supplier x month) entries")

    print(">> Building category_costs...", flush=True)
    costs = build_category_costs()
    costs.to_parquet(PROCESSED / "category_costs.parquet", index=False)
    print(f"   {len(costs):>4} categories")

    print(">> Building climate_norms...", flush=True)
    climate = build_climate_norms()
    climate.to_parquet(PROCESSED / "climate_norms.parquet", index=False)
    print(f"   {len(climate):>4} (ville x mois) profiles")

    print("\nOK -> 5 enrichissements ecrits dans data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
