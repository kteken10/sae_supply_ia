"""Configuration centrale (paths + date 'now' simulee + env-driven prod)."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

# AUDIT_LOG_PATH override-able pour la prod (volume persistant Fly.io monte sur /data)
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG_PATH", str(PROCESSED / "audit_log.jsonl")))

# Origines CORS autorisees, separees par virgule
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

# Date "now" simulee par defaut (dataset s'arrete fin 2025).
_default_now_iso = os.environ.get("DEFAULT_NOW", "2025-11-17")
DEFAULT_NOW = pd.to_datetime(_default_now_iso).date()


def parse_date(s: str | None) -> date:
    if not s:
        return DEFAULT_NOW
    return pd.to_datetime(s).date()
