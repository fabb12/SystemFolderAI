"""
backends/lmstudio.py — Backend LM Studio (modelli locali, API OpenAI-compatibile)

LM Studio espone di default un server OpenAI-compatibile su
http://localhost:1234/v1 . I modelli caricati possono essere elencati con
GET /v1/models e usati con POST /v1/chat/completions (con tool calling).

Si può sovrascrivere l'host con la variabile d'ambiente LMSTUDIO_HOST.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from fileai.backends.base import BaseBackend


DEFAULT_HOST = "http://localhost:1234"


def _host() -> str:
    return (os.environ.get("LMSTUDIO_HOST") or DEFAULT_HOST).rstrip("/")


def _http_get(url: str, timeout: float = 3.0) -> dict | None:
    try:
        import requests
    except ImportError:
        return None
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None


def _http_post(url: str, payload: dict, timeout: float = 600.0) -> dict:
    import requests
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def lista_modelli_disponibili(host: str | None = None) -> list[str]:
    """Elenca gli ID dei modelli attualmente disponibili in LM Studio."""
    base = (host or _host()).rstrip("/")
    data = _http_get(f"{base}/v1/models")
    if not data:
        return []
    items = data.get("data") or []
    nomi = [m.get("id") for m in items if isinstance(m, dict) and m.get("id")]
    return sorted(set(nomi))


class BackendLMStudio(BaseBackend):
    """Backend per LM Studio (API OpenAI chat/completions)."""

    def __init__(self, model: str, host: str | None = None):
        try:
            import requests  # noqa: F401
        except ImportError:
            print("Errore: pacchetto 'requests' non installato. Esegui: pip install requests")
            sys.exit(1)

        self.host  = (host or _host()).rstrip("/")
        self.model = model or self._primo_modello() or "local-model"

    def __str__(self) -> str:
        return f"lmstudio:{self.model}"

    def _primo_modello(self) -> str | None:
        modelli = lista_modelli_disponibili(self.host)
        return modelli[0] if modelli else None

    def chat(self, messages: list[dict]) -> tuple[str, list, dict]:
        from fileai.registry import registry

        # Converti i messaggi nel formato OpenAI puro che LM Studio si aspetta.
        oai_messages = _to_openai_messages(messages)

        payload: dict[str, Any] = {
            "model":    self.model,
            "messages": oai_messages,
            "tools":    registry.get_schema(),
            "stream":   False,
        }

        data = _http_post(f"{self.host}/v1/chat/completions", payload)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}

        testo = msg.get("content") or ""
        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append({
                "id": tc.get("id", ""),
                "function": {"name": fn.get("name", ""), "arguments": args or {}},
            })

        raw_msg = {
            "role":       "assistant",
            "content":    testo,
            "tool_calls": tool_calls,
        }
        return testo, tool_calls, raw_msg


def _to_openai_messages(messages: list[dict]) -> list[dict]:
    """
    Converte i messaggi dell'agente nel formato strettamente OpenAI:
    - tool result: role='tool', tool_call_id=..., content=str
    - assistant con tool_calls: arguments serializzato a stringa JSON
    """
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "tool":
            out.append({
                "role":          "tool",
                "tool_call_id":  m.get("tool_use_id") or m.get("tool_call_id") or "",
                "content":       str(m.get("content", "")),
            })
            continue
        if role == "assistant" and m.get("tool_calls"):
            tcs = []
            for tc in m["tool_calls"]:
                fn   = tc.get("function") or {}
                args = fn.get("arguments")
                if not isinstance(args, str):
                    args = json.dumps(args or {}, ensure_ascii=False)
                tcs.append({
                    "id":       tc.get("id", "") or f"call_{len(tcs)}",
                    "type":     "function",
                    "function": {"name": fn.get("name", ""), "arguments": args},
                })
            out.append({
                "role":       "assistant",
                "content":    m.get("content") or "",
                "tool_calls": tcs,
            })
            continue
        # system / user / plain assistant
        out.append({
            "role":    role or "user",
            "content": m.get("content", ""),
        })
    return out
