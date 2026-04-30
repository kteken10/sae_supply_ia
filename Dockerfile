# Image Docker du backend SAE Carrefour.
# Le contexte de build doit etre la racine du repo (pour acceder a data/raw/).
#
# Build localement :
#   docker build -t sae-backend .
# Run localement :
#   docker run --rm -p 8000:8000 sae-backend
FROM python:3.13-slim

# Variables runtime override-ables au deploy
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Outils de compilation pour les wheels qui en ont besoin (pyarrow / scikit-learn)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Deps Python en premier (cache layer)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Code backend + donnees brutes (les parquets sont generes au build)
COPY backend/ /app/backend/
COPY data/raw/ /app/data/raw/

# Generation des artefacts ML au build : evite d'embarquer les parquets en git
RUN cd /app/backend \
    && python etl/build_master.py \
    && python etl/enrichment.py

# Volume persistant Fly.io monte sur /data pour l'audit log (survit aux restarts)
ENV AUDIT_LOG_PATH=/data/audit_log.jsonl

# Sert sur 0.0.0.0 (Fly.io fait le port-mapping)
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/api/health || exit 1

WORKDIR /app/backend
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
