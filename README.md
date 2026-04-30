# SAE Carrefour - Analyse prescriptive de la chaine d'approvisionnement

MVP fonctionnel : ETL Python + backend FastAPI + frontend React/Vite.

## Architecture

```
SAE/
  data/
    raw/          # 5 CSV originaux (copies)
    processed/    # 4 parquets + meta.json + audit_log.jsonl
  backend/
    .venv/        # venv Python (pandas, scikit-learn, fastapi)
    etl/          # build_master.py
    app/          # FastAPI (routers, ML, audit)
  frontend/       # Vite + React 18 + Tailwind 3 + Radix
```

## Pipeline data

5 CSV harmonises en 4 artefacts parquet via `backend/etl/build_master.py` :
- `demand_daily.parquet` : demande journaliere (date, store, product) - issue des 10 000 transactions.
- `stock_snapshots.parquet` : 52 snapshots hebdo de stock par (store, product) avec flags rupture/surstock.
- `supplier_scores.parquet` : score `taux_fiabilite x (1 - retard_relatif) x pct_conforme` par fournisseur.
- `logistics_lanes.parquet` : circuits logistiques agreges (duree, cout unitaire, taux d'incident).

## ML

Forecast hebdomadaire par (store, product) avec **RandomForestRegressor** (sklearn) sur features lag/saisonnalite/promo. Intervalle 80% via ecart-type des residus in-sample.

Note : Prophet a ete envisage mais retire car CmdStan necessite un toolchain MinGW absent sur Windows par defaut. RF suffit pour 10 produits x 8 magasins x 1 an.

## Reco prescriptive

Pour chaque SKU a risque (stock <= seuil_min OU couverture < 5 jours), le moteur :
1. predit la demande sur 4 semaines,
2. calcule la quantite a commander = `forecast_4w + seuil_min - stock_actuel`,
3. selectionne le meilleur fournisseur (top score parmi ceux qui livrent ce produit),
4. choisit le circuit logistique au meilleur cout unitaire avec taux d'incident < 20%.

## IA Act

- `audit_log.jsonl` append-only : chaque validation/rejet est trace avec horodatage, operateur, decision.
- Endpoint `/api/audit/model-card` : documentation modele (donnees, features, hyperparams, limites, obligations IA Act couvertes).
- Toute reco doit etre **validee par un humain** avant execution (pas d'auto-execution).

## Lancer le projet

### 1. ETL (a faire une fois, ou apres modif des CSV)
```powershell
cd backend
.venv\Scripts\python.exe etl\build_master.py
```

### 2. Backend
```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Doc OpenAPI auto : http://127.0.0.1:8000/docs

### 3. Frontend
```powershell
cd frontend
npm install   # une fois
npm run dev
```
Ouvrir http://localhost:5173/

## Pages

| Route | Contenu |
|---|---|
| `/` | Dashboard : hero KPI, status donut, mini-stats, alerts strip, CA mensuel, alertes critiques, conformite IA Act |
| `/forecast` | Liste des SKU a risque + forecast 4 semaines + carte recommandation avec validation humaine |
| `/suppliers` | Leaderboard fournisseurs (n.1 en orange, scoring, delais, conformite) |
| `/audit` | Journal d'audit (decisions) + Model card |

## Date "now" simulee

Le dataset est fige sur 2025. Le selecteur de date en haut a droite permet de simuler n'importe quelle "date du jour" entre 2025-01-15 et 2025-12-29. Tout le dashboard recalcule alertes / forecast / recos a partir de cette date.

Defaut : 2025-11-17.

## Stack

- **Front** : React 18, Vite 6, Tailwind 3, Radix UI, recharts, react-query, sonner
- **Back** : FastAPI 0.115, pandas 2.2, scikit-learn 1.5, pyarrow 18
- **Data** : parquet + JSON, pas de DB (suffisant pour MVP fige)
