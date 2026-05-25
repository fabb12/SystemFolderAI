"""
tools/vision.py — Analisi visiva delle immagini via LLM multimodale

Dispatch automatico sul backend corrente:
  - Claude  → blocco `image` (base64) nell'API Anthropic
  - Ollama  → campo `images=[bytes]` nel chat (richiede modello vision:
              llava, qwen2.5vl, llama3.2-vision...)
  - LMStudio→ `image_url` data-URI nell'API OpenAI (richiede modello vision)
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

from fileai.registry import registry
from fileai.config import get_default_modello, parse_modello


ESTENSIONI_IMMAGINE = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic",
}

_MEDIA_TYPE = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".bmp":  "image/bmp",
    ".webp": "image/webp",
    ".heic": "image/heic",
}

# Limite: immagini più grandi vengono rifiutate (evita timeout e contesti enormi).
_MAX_BYTES = 8 * 1024 * 1024  # 8 MB


_SYSTEM_VISIONE = (
    "Sei un classificatore di immagini. Rispondi SEMPRE in italiano e SEMPRE "
    "con un singolo oggetto JSON valido, nessun testo prima o dopo, nessun "
    "blocco markdown. Usa esattamente le chiavi in italiano richieste."
)

_PROMPT_VISIONE = (
    "Analizza questa immagine e rispondi SOLO con un oggetto JSON valido "
    "(nessun testo extra, nessun ```), usando ESATTAMENTE queste chiavi in italiano:\n"
    "{\n"
    '  "soggetto": "cosa rappresenta in 1 frase",\n'
    '  "categoria": "una tra: Foto-Persone, Foto-Paesaggi, Foto-Animali, '
    "Foto-Cibo, Screenshot, Documento-Scansionato, Ricevuta, Grafica-Logo, "
    'Meme, Diagramma, Arte, Altro",\n'
    '  "sottocategoria": "specifica, es: Ritratto, Spiaggia, Gatto, Pizza, '
    'Codice, Fattura",\n'
    '  "tag": ["tag1", "tag2", "tag3"],\n'
    '  "cartella_consigliata": "NomeCartella/Sottocartella"\n'
    "}\n"
    "Esempio di risposta valida:\n"
    '{"soggetto":"Tramonto sul mare con palme","categoria":"Foto-Paesaggi",'
    '"sottocategoria":"Spiaggia","tag":["tramonto","mare","vacanza"],'
    '"cartella_consigliata":"Foto/Paesaggi"}\n'
    "Nome file: {nome}"
)


# Alias inglese → italiano: alcuni modelli (Haiku, llava piccoli) tendono a
# rispondere in inglese anche se il prompt è italiano. Normalizziamo qui.
_ALIAS = {
    "subject":          "soggetto",
    "description":      "soggetto",
    "content":          "soggetto",
    "category":         "categoria",
    "subcategory":      "sottocategoria",
    "tags":             "tag",
    "suggested_folder": "cartella_consigliata",
    "folder":           "cartella_consigliata",
    "recommended_folder": "cartella_consigliata",
}


def _normalizza_chiavi(d: dict) -> dict:
    """Mappa eventuali chiavi inglesi → italiane."""
    out: dict = {}
    for k, v in d.items():
        ki = k.lower().strip()
        out[_ALIAS.get(ki, ki)] = v
    return out


# ── Lettura immagine ──────────────────────────────────────────────

def _leggi_immagine(path: Path) -> tuple[bytes, str]:
    media = _MEDIA_TYPE.get(path.suffix.lower(), "image/jpeg")
    size = path.stat().st_size
    if size > _MAX_BYTES:
        raise RuntimeError(
            f"immagine troppo grande ({size // 1024 // 1024} MB > "
            f"{_MAX_BYTES // 1024 // 1024} MB)"
        )
    with open(path, "rb") as f:
        return f.read(), media


# ── Dispatch per backend ─────────────────────────────────────────

def _classifica_ollama(model: str, nome_file: str, data: bytes, media: str) -> str:
    from fileai.backends.ollama import _load_real_ollama, _num_ctx
    _ol = _load_real_ollama()
    prompt = _PROMPT_VISIONE.format(nome=nome_file)
    risp = _ol.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_VISIONE},
            {"role": "user", "content": prompt, "images": [data]},
        ],
        options={"num_ctx": _num_ctx(), "temperature": 0.2},
    )
    msg = risp["message"] if isinstance(risp, dict) else risp.message
    if hasattr(msg, "model_dump"):
        msg = msg.model_dump()
    elif not isinstance(msg, dict):
        msg = dict(msg)
    return msg.get("content", "") or ""


def _classifica_claude(model: str, nome_file: str, data: bytes, media: str) -> str:
    try:
        import anthropic as _anthropic
    except ImportError as e:
        raise RuntimeError(
            "Pacchetto 'anthropic' non installato (pip install anthropic)"
        ) from e
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY non impostata")
    client = _anthropic.Anthropic(api_key=api_key)
    b64 = base64.standard_b64encode(data).decode("ascii")
    prompt = _PROMPT_VISIONE.format(nome=nome_file)
    risp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_SYSTEM_VISIONE,
        temperature=0.2,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return "".join(b.text for b in risp.content if b.type == "text")


def _classifica_lmstudio(model: str, nome_file: str, data: bytes, media: str) -> str:
    try:
        import requests
    except ImportError as e:
        raise RuntimeError("Pacchetto 'requests' non installato") from e
    host = (os.environ.get("LMSTUDIO_HOST") or "http://localhost:1234").rstrip("/")
    b64 = base64.standard_b64encode(data).decode("ascii")
    prompt = _PROMPT_VISIONE.format(nome=nome_file)
    payload = {
        "model": model or "local-model",
        "messages": [
            {"role": "system", "content": _SYSTEM_VISIONE},
            {"role": "user", "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:{media};base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]},
        ],
        "max_tokens": 1024,
        "temperature": 0.2,
        "stream": False,
    }
    r = requests.post(f"{host}/v1/chat/completions", json=payload, timeout=600)
    r.raise_for_status()
    out = r.json()
    choice = (out.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content", "") or ""


def _classifica_immagine(path: Path) -> tuple[dict | None, str]:
    """Ritorna (json parsato | None, testo grezzo del modello o errore)."""
    try:
        data, media = _leggi_immagine(path)
    except Exception as e:
        return None, f"ERRORE lettura: {e}"

    kind, model = parse_modello(get_default_modello())
    try:
        if kind == "claude":
            raw = _classifica_claude(model, path.name, data, media)
        elif kind == "lmstudio":
            raw = _classifica_lmstudio(model, path.name, data, media)
        else:
            raw = _classifica_ollama(model, path.name, data, media)
    except Exception as e:
        return None, f"ERRORE backend {kind}: {e}"

    if not raw or not raw.strip():
        return None, "il modello vision non ha restituito alcun testo"

    # rimuovi eventuali code-fence markdown (```json ... ```)
    pulito = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    # cerca il primo oggetto JSON bilanciato (più robusto di .*greedy)
    candidato = _estrai_json(pulito)
    if candidato:
        try:
            d = _normalizza_chiavi(json.loads(candidato))
            return _completa_campi(d), raw
        except Exception:
            pass
    return None, raw


def _estrai_json(testo: str) -> str | None:
    """Estrae il primo oggetto JSON con bilanciamento delle graffe."""
    inizio = testo.find("{")
    if inizio < 0:
        return None
    livello = 0
    in_string = False
    escape = False
    for i in range(inizio, len(testo)):
        c = testo[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            livello += 1
        elif c == "}":
            livello -= 1
            if livello == 0:
                return testo[inizio:i + 1]
    return None


def _completa_campi(d: dict) -> dict:
    """Garantisce che le 5 chiavi attese siano presenti (fallback intelligenti)."""
    soggetto = d.get("soggetto") or d.get("descrizione") or ""
    categoria = d.get("categoria") or "Altro"
    sottocat = d.get("sottocategoria") or categoria
    tag = d.get("tag") or []
    if isinstance(tag, str):
        tag = [t.strip() for t in re.split(r"[,;]", tag) if t.strip()]
    cartella = (d.get("cartella_consigliata")
                or f"Immagini/{categoria.replace(' ', '_')}")
    return {
        "soggetto":             str(soggetto).strip() or "(non descrivibile)",
        "categoria":            str(categoria).strip() or "Altro",
        "sottocategoria":       str(sottocat).strip(),
        "tag":                  tag if isinstance(tag, list) else [str(tag)],
        "cartella_consigliata": str(cartella).strip(),
    }


def _format_risultato(d: dict) -> str:
    return (
        f"   Soggetto      : {d['soggetto']}\n"
        f"   Categoria     : {d['categoria']}\n"
        f"   Sottocategoria: {d['sottocategoria']}\n"
        f"   Tag           : {', '.join(d['tag'])}\n"
        f"   Cartella      : {d['cartella_consigliata']}"
    )


# ── Tool: singola immagine ───────────────────────────────────────

@registry.tool(
    description=(
        "Analizza VISIVAMENTE un'immagine (jpg, png, gif, bmp, webp, heic) con un "
        "modello multimodale e ne capisce il contenuto: soggetto, categoria, tag, "
        "cartella consigliata. Richiede un modello vision: Claude (qualsiasi), "
        "Ollama (llava, qwen2.5vl, llama3.2-vision), LM Studio (modello vision)."
    ),
    params={"percorso": {"type": "string", "description": "Percorso dell'immagine"}},
    required=["percorso"],
    label=("🖼️", "Analizzo l'immagine"),
)
def analisi_immagine(percorso: str) -> str:
    path = Path(percorso).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return f"ERRORE: file non trovato: {path}"
    if path.suffix.lower() not in ESTENSIONI_IMMAGINE:
        return (f"ERRORE: {path.name} non è un'immagine "
                f"({', '.join(sorted(ESTENSIONI_IMMAGINE))})")

    d, raw = _classifica_immagine(path)
    if d is None:
        if raw.startswith("ERRORE"):
            return f"🖼️ {path.name}\n   {raw[:500]}"
        # Il modello ha risposto ma non in JSON: usiamo il testo come descrizione
        descr = raw.strip().replace("\n", " ")[:300]
        return (
            f"🖼️ {path.name}\n"
            f"   Soggetto      : {descr}\n"
            f"   Categoria     : Altro\n"
            f"   Sottocategoria: (non classificata)\n"
            f"   Tag           : \n"
            f"   Cartella      : Immagini/Altro\n"
            f"   [nota: modello vision non ha restituito JSON, "
            f"usato testo come descrizione]"
        )
    return f"🖼️ {path.name}\n{_format_risultato(d)}"


# ── Tool: intera cartella ────────────────────────────────────────

@registry.tool(
    description=(
        "Analisi visiva di tutte le immagini in una cartella tramite modello "
        "multimodale. Le raggruppa per SIGNIFICATO (Foto-Paesaggi, Screenshot, "
        "Ricevute, Meme...) e suggerisce un piano di organizzazione per TEMA, "
        "non per estensione. Usalo PRIMA di spostare le immagini con sposta_file."
    ),
    params={
        "cartella": {"type": "string"},
        "max_file": {
            "type": "integer",
            "description": "Max immagini da analizzare (default 20)",
            "default": 20,
        },
    },
    required=["cartella"],
    label=("🖼️", "Analisi visiva di"),
)
def analisi_immagini_cartella(cartella: str, max_file: int = 20) -> str:
    try:
        path = Path(cartella).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: {path} non trovato"

        immagini = [
            f for f in sorted(path.iterdir())
            if f.is_file() and f.suffix.lower() in ESTENSIONI_IMMAGINE
        ]
        if not immagini:
            return f"Nessuna immagine in {path}"

        analizzate = immagini[:max_file]
        righe = [
            f"📁 Analisi visiva: {path}",
            f"   Immagini: {len(immagini)}  |  Analizzate: {len(analizzate)}\n",
        ]
        per_categoria: dict[str, list[str]] = {}
        per_cartella:  dict[str, list[str]] = {}

        for f in analizzate:
            d, raw = _classifica_immagine(f)
            righe.append("─" * 50)
            if d is None:
                righe.append(f"🖼️ {f.name}\n   {raw[:200]}")
                continue
            righe.append(f"🖼️ {f.name}\n{_format_risultato(d)}")
            cat = d.get("categoria") or "Altro"
            per_categoria.setdefault(cat, []).append(f.name)
            cs = d.get("cartella_consigliata") or cat
            per_cartella.setdefault(cs, []).append(f.name)

        if per_categoria:
            righe.append("\n" + "─" * 50)
            righe.append("📊 CATEGORIE VISIVE:")
            for cat, files in sorted(per_categoria.items(), key=lambda x: -len(x[1])):
                righe.append(f"  {cat:<24s}: {len(files)} immagini")

        if per_cartella:
            righe.append("\n📂 CARTELLE CONSIGLIATE (per significato):")
            for cs, files in sorted(per_cartella.items(), key=lambda x: -len(x[1])):
                campioni = ", ".join(files[:3])
                if len(files) > 3:
                    campioni += f" (+{len(files) - 3})"
                righe.append(f"  {cs:<28s} → {campioni}")

        if len(immagini) > max_file:
            righe.append(
                f"\n[solo le prime {max_file} analizzate — aumenta max_file se serve]"
            )

        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"
