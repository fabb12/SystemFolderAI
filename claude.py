"""
backends/claude.py — Backend Claude API (Anthropic)
"""

import os
from fileai.backends.base import BaseBackend

_SYSTEM_PROMPT_KEY = "system"


def _max_tokens() -> int:
    """Token massimi richiesti per ogni risposta Claude (env CLAUDE_MAX_TOKENS)."""
    try:
        return max(1024, int(os.environ.get("CLAUDE_MAX_TOKENS", "8192")))
    except (TypeError, ValueError):
        return 8192


class BackendClaude(BaseBackend):

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError as e:
            raise RuntimeError(
                "Pacchetto 'anthropic' non installato.\n"
                "Installa con: pip install anthropic"
            ) from e

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY non impostata.\n"
                "Imposta la chiave in Impostazioni → Modello AI → Claude API\n"
                "oppure: export ANTHROPIC_API_KEY=sk-ant-..."
            )

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

        # converti messaggi al formato Anthropic
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
            elif m["role"] == "assistant" and "tool_calls" in m:
                # assistant in formato OpenAI → blocchi Anthropic
                blocks: list[dict] = []
                testo_msg = m.get("content") or ""
                if testo_msg:
                    blocks.append({"type": "text", "text": testo_msg})
                for tc in m["tool_calls"]:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        import json as _json
                        try:
                            args = _json.loads(args) if args else {}
                        except _json.JSONDecodeError:
                            args = {}
                    blocks.append({
                        "type":  "tool_use",
                        "id":    tc.get("id", ""),
                        "name":  fn.get("name", ""),
                        "input": args,
                    })
                conv.append({"role": "assistant", "content": blocks})
            else:
                conv.append(m)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=_max_tokens(),
                system=sys_msg,
                tools=self._converti_tools(),
                messages=conv,
            )
        except self._anthropic.APIError as e:
            raise RuntimeError(f"Errore Claude API: {e}") from e

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

        raw_msg = {
            "role":       "assistant",
            "content":    testo,
            "tool_calls": tool_calls,
        }
        return testo, tool_calls, raw_msg
