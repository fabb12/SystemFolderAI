"""
tools/analysis.py — Analisi statistica e riconoscimento tipo reale (magic bytes)
"""

import zipfile
from pathlib import Path

from fileai.registry import registry

# ── Tabelle di lookup ─────────────────────────────────────────────

MAGIC_SIGNATURES: list[tuple[int, bytes, str]] = [
    (0, b'\x89PNG\r\n\x1a\n',   "image/png"),
    (0, b'\xff\xd8\xff',         "image/jpeg"),
    (0, b'GIF87a',               "image/gif"),
    (0, b'GIF89a',               "image/gif"),
    (0, b'BM',                   "image/bmp"),
    (0, b'%PDF',                 "application/pdf"),
    (0, b'\xd0\xcf\x11\xe0',    "application/msoffice"),
    (0, b'PK\x03\x04',          "application/zip"),
    (0, b'ID3',                  "audio/mp3"),
    (0, b'\xff\xfb',             "audio/mp3"),
    (0, b'OggS',                 "audio/ogg"),
    (0, b'fLaC',                 "audio/flac"),
    (0, b'\x1aE\xdf\xa3',       "video/mkv"),
    (4, b'ftyp',                 "video/mp4"),
    (0, b'\x30\x26\xb2\x75',    "video/wmv"),
    (0, b'\x1f\x8b',            "application/gzip"),
    (0, b'BZh',                  "application/bzip2"),
    (0, b'7z\xbc\xaf\x27\x1c', "application/7zip"),
    (0, b'Rar!\x1a\x07',        "application/rar"),
    (0, b'MZ',                   "application/exe"),
    (0, b'\x7fELF',              "application/elf"),
    (0, b'<?xml',                "text/xml"),
    (0, b'<html',                "text/html"),
    (0, b'<!DOCTYPE',            "text/html"),
    (0, b'#!/',                  "text/script"),
    (0, b'RIFF',                 "audio/wav"),
]

MIME_CATEGORIA: dict[str, str] = {
    "image/png":              "Immagini",
    "image/jpeg":             "Immagini",
    "image/gif":              "Immagini",
    "image/bmp":              "Immagini",
    "audio/mp3":              "Audio",
    "audio/ogg":              "Audio",
    "audio/flac":             "Audio",
    "audio/wav":              "Audio",
    "video/mp4":              "Video",
    "video/mkv":              "Video",
    "video/wmv":              "Video",
    "application/pdf":        "Documenti",
    "application/msoffice":   "Documenti",
    "application/vnd.docx":   "Documenti",
    "application/vnd.xlsx":   "Documenti",
    "application/vnd.pptx":   "Presentazioni",
    "application/zip":        "Archivi",
    "application/gzip":       "Archivi",
    "application/bzip2":      "Archivi",
    "application/7zip":       "Archivi",
    "application/rar":        "Archivi",
    "application/exe":        "Software",
    "application/elf":        "Software",
    "text/xml":               "Documenti",
    "text/html":              "Web",
    "text/script":            "Codice",
    "text/plain":             "Testo",
    "unknown":                "Altro",
}

EXT_ATTESA: dict[str, list[str]] = {
    "image/jpeg":           [".jpg", ".jpeg"],
    "image/png":            [".png"],
    "application/pdf":      [".pdf"],
    "application/vnd.docx": [".docx"],
    "application/vnd.xlsx": [".xlsx"],
    "application/vnd.pptx": [".pptx"],
    "application/exe":      [".exe"],
    "audio/mp3":            [".mp3"],
    "video/mp4":            [".mp4"],
}


# ── Funzioni interne (usate anche da altri moduli) ────────────────

def _zip_office_type(path: Path) -> str:
    """Distingue .docx / .xlsx / .pptx da un generico .zip."""
    try:
        with zipfile.ZipFile(path) as z:
            names = [n.lower() for n in z.namelist()]
            if any(n.startswith("word/") for n in names): return "application/vnd.docx"
            if any(n.startswith("xl/")   for n in names): return "application/vnd.xlsx"
            if any(n.startswith("ppt/")  for n in names): return "application/vnd.pptx"
    except Exception:
        pass
    return "application/zip"


def detect_mime(path: Path) -> str:
    """
    Rileva il MIME type reale di un file leggendo i magic bytes.
    Funzione pubblica — importata anche da semantic.py e health.py.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(32)
    except Exception:
        return "unknown"

    for offset, firma, mime in MAGIC_SIGNATURES:
        if header[offset:offset + len(firma)] == firma:
            return _zip_office_type(path) if mime == "application/zip" else mime

    try:
        header.decode("utf-8")
        return "text/plain"
    except Exception:
        return "unknown"


# ── Tool: analisi statistica ──────────────────────────────────────

@registry.tool(
    description="Analizza una cartella: statistiche per estensione e dimensione. Usa prima di organizzare.",
    params={"percorso": {"type": "string"}},
    required=["percorso"],
    label=("📊", "Analizzo le statistiche di"),
)
def analizza_cartella(percorso: str) -> str:
    try:
        path = Path(percorso).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: {path} non trovato"

        stats: dict[str, dict] = {}
        totale_size = totale_file = cartelle = 0

        for item in path.rglob("*"):
            if item.is_dir():
                cartelle += 1
                continue
            if not item.is_file():
                continue
            totale_file += 1
            ext  = item.suffix.lower() or "(nessuna)"
            size = item.stat().st_size
            totale_size += size
            if ext not in stats:
                stats[ext] = {"count": 0, "size": 0}
            stats[ext]["count"] += 1
            stats[ext]["size"]  += size

        mb = totale_size / (1024 * 1024)
        righe = [
            f"📁 {path}",
            f"   File totali  : {totale_file}",
            f"   Sottocartelle: {cartelle}",
            f"   Dimensione   : {mb:.1f} MB\n",
            "   Tipi (per frequenza):",
        ]
        for ext, d in sorted(stats.items(), key=lambda x: -x[1]["count"])[:15]:
            righe.append(f"     {ext:20s}  {d['count']:4d} file   {d['size']//1024:,} KB")
        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"


# ── Tool: scansione magic bytes ───────────────────────────────────

@registry.tool(
    description=(
        "Scansione avanzata: tipo REALE di ogni file (magic bytes), "
        "estensioni sbagliate, file senza estensione, file corrotti. "
        "Usalo PRIMA di organizzare."
    ),
    params={"cartella": {"type": "string"}},
    required=["cartella"],
    label=("🔬", "Scansione magic bytes di"),
)
def scansione_intelligente(cartella: str) -> str:
    try:
        path = Path(cartella).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: {path} non trovato"

        file_list = [f for f in path.iterdir() if f.is_file()]
        if not file_list:
            return f"Nessun file in {path}"

        per_cat:   dict[str, list] = {}
        mismatch:  list[str]       = []
        senza_ext: list[str]       = []
        corrotti:  list[str]       = []
        rows:      list[str]       = []

        for f in sorted(file_list):
            mime  = detect_mime(f)
            cat   = MIME_CATEGORIA.get(mime, "Altro")
            ext   = f.suffix.lower()
            kb    = f.stat().st_size // 1024

            per_cat.setdefault(cat, []).append(f.name)

            if not ext:
                senza_ext.append(f"{f.name}  → probabilmente {cat}")

            attese = EXT_ATTESA.get(mime, [])
            if attese and ext not in attese:
                mismatch.append(f"{f.name}  (è {mime}, ha '{ext}')")

            if f.stat().st_size < 10:
                corrotti.append(f"{f.name}  ({f.stat().st_size} B)")

            rows.append(f"  {f.name:<40s}  {cat:<15s}  {kb:>6,} KB")

        righe = [f"📁 Scansione: {path}  ({len(file_list)} file)\n", "FILE:"]
        righe.extend(rows[:60])
        if len(rows) > 60:
            righe.append(f"  ... e altri {len(rows)-60}")

        righe.append("\n📊 CATEGORIE:")
        for cat, files in sorted(per_cat.items(), key=lambda x: -len(x[1])):
            righe.append(f"  {cat:<20s}: {len(files)}")

        def sez(icona, titolo, lista):
            if lista:
                righe.append(f"\n{icona} {titolo} ({len(lista)}):")
                for x in lista[:10]: righe.append(f"  • {x}")

        sez("⚠️ ", "ESTENSIONI SBAGLIATE", mismatch)
        sez("❓", "SENZA ESTENSIONE",      senza_ext)
        sez("💀", "PROBABILMENTE CORROTTI", corrotti)

        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Identifica il tipo reale di un singolo file leggendo i magic bytes.",
    params={"percorso": {"type": "string"}},
    required=["percorso"],
    label=("🔬", "Identifico il tipo reale di"),
)
def identifica_file(percorso: str) -> str:
    path = Path(percorso).expanduser().resolve()
    if not path.exists():
        return f"ERRORE: file non trovato: {path}"
    mime     = detect_mime(path)
    cat      = MIME_CATEGORIA.get(mime, "Altro")
    ext      = path.suffix.lower()
    attese   = EXT_ATTESA.get(mime, [])
    mismatch = (f"\n   ⚠️  ESTENSIONE SBAGLIATA: è {mime} ma ha '{ext}'"
                if attese and ext not in attese else "")
    kb = path.stat().st_size // 1024
    return (f"📄 {path.name}\n"
            f"   Tipo reale : {mime}\n"
            f"   Categoria  : {cat}\n"
            f"   Dimensione : {kb:,} KB{mismatch}")
