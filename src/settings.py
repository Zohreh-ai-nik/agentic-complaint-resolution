"""Central settings for the app.

Reads configuration from (in order of trust):
1. environment variables / Function App app settings (and, in Azure, Key Vault references);
2. YAML files under ``config/`` for models, prices and thresholds.

No secrets live in this file. Secrets come from the environment only.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Repo root is two levels up from this file: src/settings.py -> repo/
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    """Load a YAML file from the config directory."""
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def models_config() -> dict[str, Any]:
    """Model names, prices and routing from config/models.yaml."""
    return _load_yaml("models.yaml")


@lru_cache(maxsize=1)
def thresholds_config() -> dict[str, Any]:
    """Limits, budgets and CI gates from config/thresholds.yaml."""
    return _load_yaml("thresholds.yaml")


def app_version() -> str:
    """App version, surfaced by the health endpoint."""
    return os.environ.get("APP_VERSION", "0.1.0")


def app_env() -> str:
    """Deployment environment name (local / uat / etc.)."""
    return os.environ.get("APP_ENV", "local")
