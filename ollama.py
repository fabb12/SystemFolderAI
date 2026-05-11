"""
backends/ollama.py — Backend Ollama (modelli locali)
"""

import sys
from fileai.backends.base import BaseBackend


class BackendOllama(BaseBackend):

    def __init__(self, model: str):
        try:
            import ollama as _ollama
            self._ollama = _ollama
        except ImportError:
            print("Errore: ollama non installato. Esegui: pip install ollama")
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
        msg        = response["message"]
        tool_calls = msg.get("tool_calls") or []
        return msg.get("content", ""), tool_calls, msg
