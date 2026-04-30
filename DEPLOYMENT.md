# Deploiement SAE Carrefour

CI/CD GitHub Actions -> Cloudflare Pages (front) + Fly.io (back).

## Architecture cible

```
sae.sden.ch          --(CF Pages)--> frontend statique React/Vite
api-sae.sden.ch      --(Fly.io)----> FastAPI + RandomForest
```

Au push sur `main` : build front + back en parallele, deploy automatique, healthcheck.

---

## 1. Setup initial (a faire UNE FOIS)

### 1.1. Pre-requis
- Compte Fly.io avec un personal access token dans GH Secrets (`FLY_API_TOKEN`)
- Compte Cloudflare avec sden.ch + token + account ID dans GH Secrets
- **flyctl en local : optionnel** (pour debug/logs). Le workflow GH Actions cree
  l'app et le volume automatiquement au premier run.

### 1.2. Creation de l'app Fly.io (auto au premier deploy)
Le workflow `.github/workflows/deploy.yml` execute :
- `flyctl status` -> si l'app n'existe pas, `flyctl apps create sae-carrefour-api --org personal`
- `flyctl volumes list` -> si le volume `audit_data` n'existe pas, `flyctl volumes create audit_data --size 1 --region cdg`
- `flyctl deploy`

Donc **rien a faire** : pousse sur main, le workflow s'occupe de tout.

Si jamais tu veux le faire manuellement avant (pour debug) :
```bash
flyctl apps create sae-carrefour-api --org personal
flyctl volumes create audit_data --size 1 --region cdg --app sae-carrefour-api
```

### 1.3. Creer le projet Cloudflare Pages
Soit via UI :
- https://dash.cloudflare.com -> Workers & Pages -> Create -> Pages -> Direct Upload
- Nom du projet : `sae-carrefour`
- Pas besoin de connecter le repo (le workflow GH Actions deploie via wrangler)

Soit via CLI (necessite wrangler local) :
```bash
npx wrangler pages project create sae-carrefour --production-branch=main
```

### 1.4. Configurer GitHub Secrets

Sur le repo : Settings -> Secrets and variables -> Actions -> New repository secret

| Secret | Comment l'obtenir |
|---|---|
| `CLOUDFLARE_API_TOKEN` | https://dash.cloudflare.com/profile/api-tokens -> Create -> Custom token avec : `Account.Cloudflare Pages.Edit`, `Zone.DNS.Edit` (zone sden.ch), `Zone.Zone.Read` (zone sden.ch) |
| `CLOUDFLARE_ACCOUNT_ID` | Visible dans le dashboard CF, en bas a droite de la page d'accueil du compte |
| `FLY_API_TOKEN` | `flyctl auth token` ou https://fly.io/user/personal_access_tokens -> Create token |

### 1.5. Configurer le custom domain Fly.io (api-sae.sden.ch)

```bash
flyctl certs create -a sae-carrefour-api api-sae.sden.ch
```
Fly te donne 2 enregistrements DNS a creer dans Cloudflare :

| Type | Nom | Cible | Proxy |
|---|---|---|---|
| `CNAME` | `api-sae` | `sae-carrefour-api.fly.dev` | DNS only (gris) |
| `CNAME` (TXT) | `_acme-challenge.api-sae` | (donne par Fly) | DNS only |

Une fois propage, valider :
```bash
flyctl certs check api-sae.sden.ch -a sae-carrefour-api
```

### 1.6. Configurer le custom domain Cloudflare Pages (sae.sden.ch)

Apres le **premier deploy** de Pages :
- Dashboard CF -> Workers & Pages -> sae-carrefour -> Custom domains -> Set up custom domain
- Domaine : `sae.sden.ch`
- Cloudflare cree automatiquement le DNS (CNAME proxified)

---

## 2. Premier deploiement

```bash
# A la racine du repo
git init
git remote add origin git@github.com:<ton-user>/sae-carrefour.git
git add .
git commit -m "Initial deploy"
git push -u origin main
```

Le workflow se declenche, ~3-4 minutes plus tard l'app est en ligne.

---

## 3. Deploiements suivants

Tout push sur `main` redeploie tout. Pour rollback :

```bash
# Backend (Fly garde l'historique des releases)
flyctl releases -a sae-carrefour-api
flyctl releases rollback <version> -a sae-carrefour-api

# Frontend (CF Pages garde l'historique des deploys)
# Dashboard CF -> Pages -> sae-carrefour -> Deployments -> Rollback
```

---

## 4. Logs et debugging

```bash
# Backend Fly
flyctl logs -a sae-carrefour-api
flyctl status -a sae-carrefour-api
flyctl ssh console -a sae-carrefour-api    # shell dans le container

# Frontend CF Pages
# Dashboard -> Pages -> sae-carrefour -> Deployments -> click sur un deploy
```

---

## 5. Variables d'environnement

### Backend (Fly.io)
Definies dans `fly.toml` (`[env]`). Pour un secret :
```bash
flyctl secrets set NAME=value -a sae-carrefour-api
```
Notre app n'a pas de secret runtime au-dela de la config publique.

### Frontend (Cloudflare Pages)
`VITE_API_BASE_URL` est injecte au build via le workflow GitHub Actions. Pour le changer :
- Editer `.github/workflows/deploy.yml` -> step "Build" -> `env: VITE_API_BASE_URL`

---

## 6. Couts

Avec le free tier :
- **Fly.io** : 1 shared-cpu-1x 256MB + 1 GB volume = gratuit (limite 3 VMs)
- **Cloudflare Pages** : illimite en static + 500 builds/mois gratuit
- **Cloudflare DNS** : gratuit
- **Domaine sden.ch** : separement

Total recurring : 0 EUR.

---

## 7. Checklist avant l'oral

- [ ] `flyctl status -a sae-carrefour-api` -> `started`
- [ ] `curl https://api-sae.sden.ch/api/health` -> `{"status":"ok",...}`
- [ ] `https://sae.sden.ch` charge le dashboard
- [ ] Date "now" selecteur fonctionne
- [ ] Toggle enrichissements fonctionne
- [ ] Validation d'une reco apparait dans /audit
- [ ] Rotater les tokens utilises pour le setup initial !

---

## 8. Que faire si ca casse

### Le backend ne demarre pas
```bash
flyctl logs -a sae-carrefour-api
# Si erreur d'import : verifier que data/raw/*.csv ont bien ete copies (cf .dockerignore)
# Si OOM : augmenter memory_mb dans fly.toml
```

### Le frontend affiche "Network Error"
- Verifier le DNS : `dig api-sae.sden.ch`
- Verifier le certificat : `flyctl certs check api-sae.sden.ch -a sae-carrefour-api`
- Verifier CORS : la valeur de `CORS_ORIGINS` dans `fly.toml` doit matcher `https://sae.sden.ch` exactement

### La machine Fly s'eteint trop souvent
Mettre `min_machines_running = 1` dans `fly.toml` (consomme un peu plus de ressources).
