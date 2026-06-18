"""
tools/history.py — Cronologia operazioni e rollback (annullamento)
====================================================================

Tiene un journal persistente delle operazioni di modifica eseguite dai tool
del filesystem (spostamenti, rinomine, creazioni, copie, compressioni) così da
poterle annullare (rollback).

Ogni operazione registra una lista di *passi inversi* — istruzioni che, eseguite
in ordine, riportano il filesystem allo stato precedente:

  {"op": "move",  "from": X, "to": Y}  → sposta X in Y
  {"op": "rmdir", "path": P}           → rimuove la cartella P SOLO se vuota
  {"op": "rm",    "path": P}           → rimuove file/cartella P (es. una copia)

Il journal è salvato in ``~/.fileai_history.json`` (ultime _MAX_VOCI voci).
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from fileai.registry import registry

S = {"type": "string"}
I = {"type": "integer"}

_HISTORY_FILE = Path.home() / ".fileai_history.json"
_MAX_VOCI = 200


# ── Persistenza ───────────────────────────────────────────────────

def _carica() -> list[dict]:
    try:
        if _HISTORY_FILE.exists():
            data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _salva(voci: list[dict]) -> None:
    try:
        _HISTORY_FILE.write_text(
            json.dumps(voci[-_MAX_VOCI:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # la cronologia è best-effort: non deve mai far fallire un'operazione
        pass


def registra_operazione(tipo: str, descrizione: str, passi_inversi: list[dict]) -> None:
    """
    Registra un'operazione reversibile nel journal.

    Chiamata dai tool del filesystem dopo un'operazione andata a buon fine.
    È volutamente tollerante agli errori: se qualcosa va storto non solleva
    eccezioni, per non compromettere l'operazione già eseguita.
    """
    if not passi_inversi:
        return
    try:
        voci = _carica()
        voci.append({
            "tipo":        tipo,
            "descrizione": descrizione,
            "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "passi":       passi_inversi,
        })
        _salva(voci)
    except Exception:
        pass


# ── Esecuzione passi inversi ──────────────────────────────────────

def _esegui_passo(passo: dict) -> str:
    op = passo.get("op")
    try:
        if op == "move":
            src = Path(passo["from"])
            dst = Path(passo["to"])
            if not src.exists():
                return f"⏭️  non trovato (già spostato?): {src}"
            if dst.exists():
                return f"ERRORE: destinazione occupata, salto: {dst}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"↩️  {src.name}  →  {dst}"

        if op == "rmdir":
            p = Path(passo["path"])
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
                return f"🗑️  cartella rimossa: {p}"
            return f"⏭️  cartella non vuota o assente, salto: {p}"

        if op == "rm":
            p = Path(passo["path"])
            if p.exists():
                shutil.rmtree(str(p)) if p.is_dir() else p.unlink()
                return f"🗑️  rimosso: {p}"
            return f"⏭️  già assente: {p}"

        return f"ERRORE: passo sconosciuto: {op}"
    except Exception as e:
        return f"ERRORE durante l'annullamento ({op}): {e}"


# ── Tool: annulla ─────────────────────────────────────────────────

@registry.tool(
    description=(
        "Annulla (rollback) le ultime operazioni di modifica eseguite: "
        "spostamenti, rinomine, creazioni di cartelle e copie tornano allo "
        "stato precedente. Usa 'quante' per annullare più operazioni partendo "
        "dalla più recente. NOTA: le eliminazioni di file NON sono reversibili."
    ),
    params={
        "quante": {**I, "description": "Quante operazioni annullare (dalla più recente)", "default": 1},
    },
    required=[],
    label=("↩️ ", "Annullo le ultime operazioni"),
)
def annulla_ultima_operazione(quante: int = 1) -> str:
    voci = _carica()
    if not voci:
        return "Nessuna operazione da annullare."

    try:
        quante = max(1, int(quante))
    except (TypeError, ValueError):
        quante = 1

    da_annullare = voci[-quante:]
    rimaste      = voci[: len(voci) - len(da_annullare)]

    righe: list[str] = [f"✅ Annullate {len(da_annullare)} operazione/i:\n"]
    # annulla dalla più recente alla più vecchia
    for voce in reversed(da_annullare):
        righe.append(f"↩️  {voce.get('descrizione', '?')}  "
                     f"[{voce.get('timestamp', '?')}]")
        for passo in voce.get("passi", []):
            righe.append("   " + _esegui_passo(passo))

    _salva(rimaste)
    return "\n".join(righe)


# ── Tool: cronologia ──────────────────────────────────────────────

@registry.tool(
    description=(
        "Mostra la cronologia delle ultime operazioni di modifica eseguite "
        "(utile per decidere cosa annullare con annulla_ultima_operazione)."
    ),
    params={
        "quante": {**I, "description": "Quante voci mostrare", "default": 10},
    },
    required=[],
    label=("📜", "Leggo la cronologia"),
)
def mostra_cronologia(quante: int = 10) -> str:
    voci = _carica()
    if not voci:
        return "Cronologia vuota: nessuna operazione registrata."

    try:
        quante = max(1, int(quante))
    except (TypeError, ValueError):
        quante = 10

    ultime = voci[-quante:]
    righe  = [f"Cronologia operazioni (ultime {len(ultime)} di {len(voci)}):\n"]
    # la più recente in cima
    for i, voce in enumerate(reversed(ultime), 1):
        righe.append(f"  {i}. [{voce.get('timestamp', '?')}] "
                     f"{voce.get('descrizione', '?')}")
    return "\n".join(righe)
