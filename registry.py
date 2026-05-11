"""
registry.py — Tool Registry (pattern Plugin)
=============================================
Ogni tool è una funzione Python decorata con @registry.tool().
Il Registry raccoglie automaticamente:
  - la funzione da eseguire
  - lo schema JSON da passare al LLM
  - l'etichetta per la UI

Aggiungere un nuovo tool = decorare una funzione.
Non serve modificare nessun altro file.

Uso:
    from fileai.registry import registry

    @registry.tool(
        description="Fa qualcosa di utile",
        params={"percorso": {"type": "string"}},
        required=["percorso"],
        label=("🔧", "Faccio qualcosa su"),
    )
    def mio_tool(percorso: str) -> str:
        ...
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolEntry:
    name:     str
    fn:       Callable
    schema:   dict          # schema OpenAI/Ollama
    label:    tuple[str, str]  # (icona, verbo) per la UI


class ToolRegistry:
    """
    Registro centrale di tutti i tool disponibili.
    Unica istanza globale: `registry`.
    """

    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    # ── decoratore ───────────────────────────────────────────────

    def tool(
        self,
        description: str,
        params: dict | None = None,
        required: list[str] | None = None,
        label: tuple[str, str] = ("⚙️", "Eseguo"),
    ):
        """
        Decoratore che registra una funzione come tool.

        @registry.tool(
            description="...",
            params={"arg": {"type": "string"}},
            required=["arg"],
            label=("🔧", "Faccio"),
        )
        def mia_funzione(arg: str) -> str: ...
        """
        def decorator(fn: Callable) -> Callable:
            name = fn.__name__
            self._tools[name] = ToolEntry(
                name=name,
                fn=fn,
                schema={
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": params or {},
                            "required": required or [],
                        },
                    },
                },
                label=label,
            )
            return fn
        return decorator

    # ── accesso ai dati ──────────────────────────────────────────

    def get_schema(self) -> list[dict]:
        """Lista di schemi da passare al LLM."""
        return [entry.schema for entry in self._tools.values()]

    def get_label(self, name: str) -> tuple[str, str]:
        entry = self._tools.get(name)
        return entry.label if entry else ("⚙️", name)

    def esegui(self, name: str, argomenti: dict) -> str:
        """Esegue un tool per nome con gli argomenti dati."""
        entry = self._tools.get(name)
        if not entry:
            disponibili = list(self._tools.keys())
            return f"Tool '{name}' non esiste. Disponibili: {disponibili}"
        try:
            return str(entry.fn(**argomenti))
        except TypeError as e:
            return f"Argomenti errati per '{name}': {e}"
        except Exception as e:
            return f"Errore in '{name}': {e}"

    def nomi(self) -> list[str]:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Istanza globale — importata da tutti i moduli
registry = ToolRegistry()
