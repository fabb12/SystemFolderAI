"""
config.py — Configurazione persistente e parsing del modello
"""

import json
from pathlib import Path

CONFIG_PATH     = Path.home() / ".fileai.json"
DEFAULT_MODELLO = "ollama:llama3.1"

CLAUDE_MODELS = {
    "sonnet":  "claude-sonnet-4-20250514",
    "opus":    "claude-opus-4-5",
    "haiku":   "claude-haiku-4-5-20251001",
    "default": "claude-sonnet-4-20250514",
}


# ── Config persistente ────────────────────────────────────────────

def leggi_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
    except Exception:
        pass
    return {"default_modello": DEFAULT_MODELLO}


def scrivi_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as e:
        print(f"⚠️  Impossibile salvare config: {e}")


def get_default_modello() -> str:
    return leggi_config().get("default_modello", DEFAULT_MODELLO)


def set_default_modello(spec: str) -> None:
    cfg = leggi_config()
    cfg["default_modello"] = spec
    scrivi_config(cfg)


# ── Parsing spec modello ──────────────────────────────────────────

def parse_modello(spec: str) -> tuple[str, str]:
    """
    Parsifica la stringa modello → (backend, model_name).

    "ollama"               → ("ollama", "llama3.1")
    "ollama:qwen2.5"       → ("ollama", "qwen2.5")
    "claude"               → ("claude", "claude-sonnet-4-20250514")
    "claude:opus"          → ("claude", "claude-opus-4-5")
    "lmstudio"             → ("lmstudio", "")    (auto: primo disponibile)
    "lmstudio:<model-id>"  → ("lmstudio", "<model-id>")
    """
    spec = spec.strip()
    # rendiamo lowercase solo il backend, non il nome modello
    backend_part, sep, model = spec.partition(":")
    backend = backend_part.strip().lower()
    model = model.strip()

    if backend == "claude":
        full = CLAUDE_MODELS.get(model.lower(), model or CLAUDE_MODELS["default"])
        return "claude", full

    if backend in ("lmstudio", "lm-studio", "lms"):
        return "lmstudio", model

    return "ollama", (model or "llama3.1")


def modello_da_args(args) -> str:
    """Priorità: -m nel comando > default in config > hardcoded."""
    m = getattr(args, "modello", None)
    return m if m else get_default_modello()
