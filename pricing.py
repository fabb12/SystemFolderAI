"""
pricing.py — Tariffe API e calcolo costo per i modelli a pagamento.

Alla fine di ogni operazione l'agente mostra quanti token sono stati
consumati e quanto può essere costata la chiamata (solo per backend
fatturati, es. Claude API). I modelli locali (Ollama, LM Studio) sono
gratuiti, quindi viene mostrato solo il conteggio token.

⚠️ Le tariffe Claude sono codificate qui sotto e verificate al
   `PRICING_VERIFIED_AT`. Quando Anthropic aggiorna i prezzi:
   1. apri https://docs.anthropic.com/en/docs/about-claude/pricing
   2. aggiorna le righe nella tabella `_CLAUDE_PRICING`
   3. aggiorna `PRICING_VERIFIED_AT` con la data di oggi

Il match per modello è per sottostringa: nuovi snapshot della stessa
famiglia (es. `claude-sonnet-4-5-XXX`) ereditano automaticamente il
prezzo della famiglia, finché Anthropic non cambia la tariffa.
"""

from __future__ import annotations

from typing import Optional

# Data di ultima verifica delle tariffe (YYYY-MM).
PRICING_VERIFIED_AT = "2026-01"

# Tabella tariffe Claude: USD per 1 milione di token.
# L'ordine conta — la prima riga in cui *uno* degli alias compare nel
# nome del modello vince. Gli alias coprono entrambe le convenzioni di
# naming usate da Anthropic:
#   nuova (4.x):  claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001
#   vecchia (3.x): claude-3-5-haiku-20241022, claude-3-opus-20240229
_CLAUDE_PRICING: tuple[tuple[tuple[str, ...], dict], ...] = (
    # Haiku — modelli leggeri
    (("haiku-4",),                 {"input": 1.0,  "output": 5.0}),
    (("haiku-3-5", "3-5-haiku"),   {"input": 0.80, "output": 4.0}),
    (("haiku-3",   "3-haiku"),     {"input": 0.25, "output": 1.25}),
    # Sonnet — modelli bilanciati
    (("sonnet-4",),                {"input": 3.0,  "output": 15.0}),
    (("sonnet-3-7", "3-7-sonnet"), {"input": 3.0,  "output": 15.0}),
    (("sonnet-3-5", "3-5-sonnet"), {"input": 3.0,  "output": 15.0}),
    (("sonnet-3",   "3-sonnet"),   {"input": 3.0,  "output": 15.0}),
    # Opus — modelli premium
    (("opus-4",),                  {"input": 15.0, "output": 75.0}),
    (("opus-3", "3-opus"),         {"input": 15.0, "output": 75.0}),
)

# Moltiplicatori sul prezzo input per i token speciali Anthropic.
# Riferimento: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
_CACHE_WRITE_MULT = 1.25   # cache_creation_input_tokens (scrittura cache 5m)
_CACHE_READ_MULT  = 0.10   # cache_read_input_tokens     (lettura cache)


def get_claude_pricing(model: str) -> Optional[dict]:
    """Ritorna `{'input': $/Mtok, 'output': $/Mtok}` per il modello dato.

    Match per sottostringa case-insensitive. `None` se il modello non è
    in tabella — il chiamante deve gestire il caso "tariffa sconosciuta".
    """
    if not model:
        return None
    key = model.lower()
    for aliases, prices in _CLAUDE_PRICING:
        if any(a in key for a in aliases):
            return prices
    return None


def calcola_costo_claude(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write: int = 0,
    cache_read: int = 0,
) -> Optional[float]:
    """Costo in USD per una serie di chiamate Claude. `None` se tariffa ignota."""
    p = get_claude_pricing(model)
    if not p:
        return None
    inp = p["input"]
    out = p["output"]
    totale = (
        input_tokens  * inp
        + output_tokens * out
        + cache_write   * inp * _CACHE_WRITE_MULT
        + cache_read    * inp * _CACHE_READ_MULT
    )
    return totale / 1_000_000


def formatta_costo(usd: float) -> str:
    """Formatta un costo USD con precisione adeguata alla grandezza."""
    if usd <= 0:
        return "$0"
    if usd < 0.001:
        return f"${usd*100:.4f}¢"   # in centesimi
    if usd < 0.01:
        return f"${usd:.5f}"
    if usd < 1.0:
        return f"${usd:.4f}"
    return f"${usd:.3f}"


def formatta_riepilogo_uso(uso: dict, model: str, backend_kind: str) -> str:
    """Riga di riepilogo da stampare a fine task.

    `uso` atteso:
        {"input": int, "output": int, "cache_write": int,
         "cache_read": int, "chiamate": int}
    """
    inp   = int(uso.get("input", 0))
    out   = int(uso.get("output", 0))
    cw    = int(uso.get("cache_write", 0))
    cr    = int(uso.get("cache_read", 0))
    calls = int(uso.get("chiamate", 0))
    tot   = inp + out + cw + cr

    if tot == 0 and calls == 0:
        return ""

    parti = [f"{calls} chiamat" + ("a" if calls == 1 else "e") + " al modello"]
    parti.append(f"{inp + cw + cr} token in")
    parti.append(f"{out} token out")
    if cw or cr:
        parti.append(f"cache scritta {cw} / letta {cr}")
    parti.append(f"totale {tot}")
    riga_token = "  ·  ".join(parti)

    if backend_kind == "claude":
        costo = calcola_costo_claude(model, inp, out, cw, cr)
        if costo is None:
            riga_costo = (
                f"💰 Costo stimato: ignoto — tariffa per '{model}' non in tabella. "
                f"Verifica su docs.anthropic.com/pricing e aggiorna pricing.py."
            )
        else:
            riga_costo = (
                f"💰 Costo stimato: {formatta_costo(costo)} USD  "
                f"(tariffe verificate {PRICING_VERIFIED_AT})"
            )
        return f"📊 Uso: {riga_token}\n{riga_costo}"

    # backend locale → gratuito
    return f"📊 Uso: {riga_token}  ·  💰 Gratis (modello locale)"
