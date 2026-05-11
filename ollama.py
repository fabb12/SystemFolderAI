"""
backends/ollama.py — Backend Ollama (modelli locali)

Nota: questo file si chiama 'ollama.py' come il package PyPI. Per evitare
che `import ollama` ricarichi questo stesso file (shadow) usiamo un loader
dedicato che cerca il vero pacchetto saltando la directory locale.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fileai.backends.base import BaseBackend


# ── Loader del package reale ────────────────────────────────────────

def _load_real_ollama():
    """Carica il package PyPI `ollama` evitando lo shadow di questo file."""
    import importlib
    import importlib.util
    from importlib.machinery import PathFinder

    here = Path(__file__).resolve().parent

    # Se in sys.modules c'è già qualcosa che è il NOSTRO file, rimuovilo.
    cached = sys.modules.get("ollama")
    if cached is not None:
        cached_file = getattr(cached, "__file__", "") or ""
        if cached_file and Path(cached_file).resolve() == Path(__file__).resolve():
            sys.modules.pop("ollama", None)
        elif hasattr(cached, "chat"):
            return cached  # già il vero pacchetto

    # Cerca il pacchetto in sys.path escludendo la nostra cartella.
    paths = [p for p in sys.path if p and Path(p).resolve() != here]
    spec = PathFinder.find_spec("ollama", paths)
    if spec is None:
        raise ImportError(
            "Pacchetto Python 'ollama' non trovato. Installa con: pip install ollama"
        )

    mod = importlib.util.module_from_spec(spec)
    sys.modules["ollama"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _ollama_client(host: str | None = None):
    """Ritorna un Client del pacchetto ollama, opzionalmente con host custom."""
    pkg = _load_real_ollama()
    if host:
        return pkg.Client(host=host)
    return pkg


def lista_modelli_disponibili(host: str | None = None) -> list[str]:
    """
    Elenca i modelli Ollama installati localmente.
    Ritorna una lista di nomi (es. ['llama3.1:latest', 'qwen2.5:7b']).
    """
    try:
        client = _ollama_client(host)
        resp = client.list()
        # API moderna: ollama.ListResponse(models=[Model(model='...', ...)])
        # API legacy:  dict {"models": [{"name": "..."} | {"model": "..."}]}
        modelli = getattr(resp, "models", None)
        if modelli is None and isinstance(resp, dict):
            modelli = resp.get("models", [])
        nomi: list[str] = []
        for m in modelli or []:
            nome = getattr(m, "model", None) or getattr(m, "name", None)
            if not nome and isinstance(m, dict):
                nome = m.get("model") or m.get("name")
            if nome:
                nomi.append(nome)
        return sorted(set(nomi))
    except Exception:
        return []


# ── Backend ─────────────────────────────────────────────────────────

class BackendOllama(BaseBackend):

    def __init__(self, model: str):
        try:
            self._ollama = _load_real_ollama()
        except ImportError as e:
            print(f"Errore: {e}")
            sys.exit(1)
        self.model = model

    def __str__(self) -> str:
        return f"ollama:{self.model}"

    def chat(self, messages: list[dict]) -> tuple[str, list, dict]:
        from fileai.registry import registry
        response   = self._ollama.chat(
            model=self.model,
            messages=messages,
            tools=registry.get_schema(),
        )
        msg        = response["message"] if isinstance(response, dict) else response.message
        if hasattr(msg, "model_dump"):
            msg = msg.model_dump()
        elif not isinstance(msg, dict):
            msg = dict(msg)
        tool_calls = msg.get("tool_calls") or []
        return msg.get("content", "") or "", tool_calls, msg
