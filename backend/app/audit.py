"""Log audit (IA Act): persistance JSONL des recommandations et validations."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .config import AUDIT_LOG


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def append_event(event_type: str, payload: dict[str, Any]) -> dict:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": _now_iso(),
        "type": event_type,
        **payload,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_events(limit: int = 100) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out.reverse()  # plus recent en premier
    return out
