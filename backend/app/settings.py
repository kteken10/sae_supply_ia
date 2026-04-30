"""Etat d'execution paramétrable (toggle enrichissements)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeSettings:
    use_enriched: bool = True


_settings = RuntimeSettings()


def get_settings() -> RuntimeSettings:
    return _settings


def set_use_enriched(flag: bool) -> RuntimeSettings:
    _settings.use_enriched = bool(flag)
    return _settings
