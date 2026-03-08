from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("SENTINEL_DATA_DIR", str(PROJECT_ROOT / "data")))

# Gemini LLM — supports API key (simple) or Vertex AI (service account)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# PostgreSQL (AIML instance, sentinel schema)
PG_HOST = os.environ.get("AIML_POSTGRES_HOST", "localhost")
PG_PORT = int(os.environ.get("AIML_POSTGRES_PORT", "5433"))
PG_DB = os.environ.get("AIML_POSTGRES_DB", "aiml")
PG_USER = os.environ.get("AIML_POSTGRES_USER", "aiml_user")
PG_PASSWORD = os.environ.get("AIML_POSTGRES_PASSWORD", "aiml_dev_password")

# Auth
ADMIN_EMAIL = os.environ.get("SENTINEL_ADMIN_EMAIL", "admin@engine.local")
ADMIN_PASSWORD = os.environ.get("SENTINEL_ADMIN_PASSWORD", "Sentinel1!")
JWT_SECRET = os.environ.get("SENTINEL_JWT_SECRET", "sentinel-dev-jwt-secret")
SESSION_EXPIRY_HOURS = int(os.environ.get("SENTINEL_SESSION_HOURS", "72"))

# Agent settings
AGENT_CYCLE_SECONDS = int(os.environ.get("AGENT_CYCLE_SECONDS", "15"))
MAX_TILES = int(os.environ.get("MAX_TILES", "50"))

# CORS origins — comma-separated, defaults to "*" for dev
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# Silo palette (assigned to discovered silos in order)
SILO_PALETTE = [
    {"color": "#818cf8", "bg": "rgba(129,140,248,0.08)", "border": "rgba(129,140,248,0.2)"},
    {"color": "#f59e0b", "bg": "rgba(245,158,11,0.08)", "border": "rgba(245,158,11,0.2)"},
    {"color": "#34d399", "bg": "rgba(52,211,153,0.08)", "border": "rgba(52,211,153,0.2)"},
    {"color": "#f472b6", "bg": "rgba(244,114,182,0.08)", "border": "rgba(244,114,182,0.2)"},
    {"color": "#60a5fa", "bg": "rgba(96,165,250,0.08)", "border": "rgba(96,165,250,0.2)"},
    {"color": "#a78bfa", "bg": "rgba(167,139,250,0.08)", "border": "rgba(167,139,250,0.2)"},
]

ALPHA_SILO = {
    "id": "alpha",
    "label": "Cross-Silo",
    "color": "#ffffff",
    "bg": "rgba(255,255,255,0.08)",
    "border": "rgba(255,255,255,0.45)",
}

# User-defined silo themes. The LLM will map these to actual data columns.
# Set to None or [] to let the LLM choose freely from the data.
# Examples: ["doctors", "orders", "training", "products"]
SILO_HINTS: Optional[List[str]] = None

# Row configuration — two dynamic rows + saved interactions (fixed)
# Each row has an id, label, icon, and a description that guides the LLM
DEFAULT_ROW_CONFIG = [
    {
        "id": "row1",
        "label": "Needs Attention",
        "icon": "▲",
        "bright": True,
        "description": "Anomalies, outliers, significant deviations from expected patterns, urgent issues requiring action",
    },
    {
        "id": "row2",
        "label": "Monitoring",
        "icon": "●",
        "bright": False,
        "description": "Emerging trends, recurring patterns, metrics to watch, gradual shifts worth tracking",
    },
]
