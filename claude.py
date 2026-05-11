"""
backends/claude.py — Backend Claude API (Anthropic)
"""

import os
import sys
from fileai.backends.base import BaseBackend

_SYSTEM_PROMPT_KEY = "system"


class BackendClaude(BaseBackend):

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError:
            print("Errore: anthropic non installato. Esegui: pip install anthropic")
            sys.exit(1)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Errore: ANTHROPIC_API_KEY non impostata.")
            print("  export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)

        self.model  = model
        self.client = self._anthropic.Anthropic(api_key=api_key)

    def __str__(self) -> str:
        return f"claude:{self.model}"

    def _converti_tools(self) -> list[dict]:
        """Converte schema OpenAI → schema Anthropic."""
        from fileai.registry import registry
        result = []
        for entry in registry.get_schema():
            f = entry["function"]
            result.append({
                "name":         f["name"],
                "description":  f["description"],
                "input_schema": f["parameters"],
            })
        return result

    def chat(self, messages: list[dict]) -> tuple[str, list, dict]:
        from fileai.agent import SYSTEM_PROMPT

        # Claude vuole system separato dai messaggi
        sys_msg = next(
            (m["content"] for m in messages if m["role"] == _SYSTEM_PROMPT_KEY),
            SYSTEM_PROMPT,
        )
        msgs = [m for m in messages if m["role"] != _SYSTEM_PROMPT_KEY]

        # converti tool_results al formato Anthropic
        conv = []
        for m in msgs:
            if m["role"] == "tool":
                conv.append({
                    "role": "user",
                    "content": [{
                        "type":        "tool_result",
                        "tool_use_id": m.get("tool_use_id", ""),
                        "content":     m["content"],
                    }],
                })
            else:
                conv.append(m)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=sys_msg,
            tools=self._converti_tools(),
            messages=conv,
        )

        testo      = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                testo += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "function": {"name": block.name, "arguments": block.input},
                    "id": block.id,
                })

        return testo, tool_calls, {"content": testo, "tool_calls": tool_calls}
