"""
tools/semantic.py — Analisi semantica dei documenti via LLM
"""

import json
import re
import zipfile
from pathlib import Path

from fileai.registry import registry
from fileai.config import get_default_modello, parse_modello

ESTENSIONI_TESTO = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".py", ".js",
    ".ts", ".java", ".cpp", ".c", ".h", ".log", ".ini", ".cfg",
    ".yaml", ".yml", ".toml", ".rst", ".tex",
}


# ── Estrazione testo ──────────────────────────────────────────────

def estrai_testo(path: Path, max_chars: int = 1500) -> str:
    """Estrae testo leggibile da un documento."""
    ext = path.suffix.lower()

    if ext in ESTENSIONI_TESTO:
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception:
            return ""

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            testo  = ""
            for page in reader.pages[:3]:
                testo += page.extract_text() or ""
                if len(testo) >= max_chars:
                    break
            return testo[:max_chars]
        except ImportError:
            return "(PDF — installa pypdf: pip install pypdf)"
        except Exception:
            return ""

    if ext == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="replace")
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml)).strip()[:max_chars]
        except Exception:
            return ""

    return ""


# ── Chiamata LLM per classificazione ─────────────────────────────

def _classifica_con_llm(nome_file: str, testo: str) -> str:
    """
    Manda il testo al LLM locale (Ollama) e riceve classificazione JSON.
    """
    prompt = (
        f'Analizza questo documento e rispondi SOLO con JSON valido:\n'
        f'{{"argomento":"di cosa tratta in 1 frase",'
        f'"categoria":"una tra Lavoro Finanza Personale Tecnico Istruzione Legale Salute Creativo Altro",'
        f'"sottocategoria":"specifica es Fatture Contratti Note Codice Ricette",'
        f'"tag":["tag1","tag2","tag3"],'
        f'"cartella_consigliata":"NomeCartella/Sottocartella"}}\n\n'
        f'Documento ({nome_file}):\n---\n{testo[:1200]}\n---'
    )
    try:
        import ollama as _ollama
        _, model_name = parse_modello(get_default_modello())
        risposta = _ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )["message"]["content"].strip()
    except Exception as e:
        return f"ERRORE LLM: {e}"

    m = re.search(r'\{.*\}', risposta, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group())
            return (
                f"   Argomento     : {d.get('argomento','?')}\n"
                f"   Categoria     : {d.get('categoria','?')}\n"
                f"   Sottocategoria: {d.get('sottocategoria','?')}\n"
                f"   Tag           : {', '.join(d.get('tag',[]))}\n"
                f"   Cartella      : {d.get('cartella_consigliata','?')}"
            ), d.get("categoria", "Altro")
        except Exception:
            pass
    return risposta, "Altro"


# ── Tool: analisi singolo documento ──────────────────────────────

@registry.tool(
    description=(
        "Legge il contenuto di un documento (txt, md, pdf, docx, csv, py...) "
        "e usa l'AI per capire l'argomento, la categoria e suggerisce la cartella. "
        "Usa per organizzare per SIGNIFICATO, non solo per tipo di file."
    ),
    params={"percorso": {"type": "string", "description": "Percorso del documento"}},
    required=["percorso"],
    label=("🧠", "Analizzo semanticamente"),
)
def analisi_semantica(percorso: str) -> str:
    path = Path(percorso).expanduser().resolve()
    if not path.exists():
        return f"ERRORE: file non trovato: {path}"

    testo = estrai_testo(path)
    if not testo.strip():
        return f"Impossibile estrarre testo da {path.name}"

    risultato, _ = _classifica_con_llm(path.name, testo)
    return f"📄 {path.name}\n{risultato}"


# ── Tool: analisi intera cartella ─────────────────────────────────

@registry.tool(
    description=(
        "Analisi semantica di tutti i documenti in una cartella. "
        "Suggerisce come organizzarli per CONTENUTO, non solo per estensione. "
        "Analizza al massimo max_file documenti."
    ),
    params={
        "cartella": {"type": "string"},
        "max_file": {"type": "integer", "description": "Max file da analizzare (default 20)", "default": 20},
    },
    required=["cartella"],
    label=("🧠", "Analisi semantica di"),
)
def analisi_semantica_cartella(cartella: str, max_file: int = 20) -> str:
    from fileai.tools.analysis import detect_mime, MIME_CATEGORIA

    try:
        path = Path(cartella).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: {path} non trovato"

        # raccogli file analizzabili
        candidati = []
        for f in path.iterdir():
            if not f.is_file():
                continue
            ext  = f.suffix.lower()
            mime = detect_mime(f)
            if ext in ESTENSIONI_TESTO or mime in (
                "application/pdf", "application/vnd.docx", "application/vnd.xlsx"
            ):
                candidati.append(f)

        if not candidati:
            return f"Nessun documento analizzabile in {path}"

        analizzati = candidati[:max_file]
        righe = [
            f"📁 Analisi semantica: {path}",
            f"   Documenti: {len(candidati)}  |  Analizzati: {len(analizzati)}\n",
        ]
        per_categoria: dict[str, list] = {}

        for f in analizzati:
            testo = estrai_testo(f)
            if not testo.strip():
                righe.append(f"─ {f.name}: impossibile estrarre testo")
                continue
            risultato, cat = _classifica_con_llm(f.name, testo)
            righe.append("─" * 50)
            righe.append(f"📄 {f.name}\n{risultato}")
            per_categoria.setdefault(cat, []).append(f.name)

        if per_categoria:
            righe.append("\n" + "─" * 50)
            righe.append("📊 CATEGORIE SEMANTICHE SUGGERITE:")
            for cat, files in sorted(per_categoria.items(), key=lambda x: -len(x[1])):
                righe.append(f"  {cat:<20s}: {len(files)} file")

        if len(candidati) > max_file:
            righe.append(f"\n[solo i primi {max_file} analizzati — aumenta max_file se necessario]")

        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"
