"""
tools/filesystem.py — Operazioni su file e cartelle
"""

import shutil
from pathlib import Path

from fileai.registry import registry

S = {"type": "string"}
B = {"type": "boolean"}
I = {"type": "integer"}


@registry.tool(
    description="Elenca file e sottocartelle. Usalo per vedere cosa c'è prima di agire.",
    params={
        "percorso":  {**S, "description": "Percorso della cartella"},
        "ricorsivo": {**B, "description": "Se true elenca anche sottocartelle", "default": False},
        "pattern":   {**S, "description": "Filtro glob es: '*.pdf'", "default": "*"},
    },
    required=["percorso"],
    label=("🔍", "Leggo il contenuto di"),
)
def lista_cartella(percorso: str, ricorsivo: bool = False, pattern: str = "*") -> str:
    try:
        path = Path(percorso).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: percorso non trovato: {path}"
        if not path.is_dir():
            return f"ERRORE: '{path}' non è una cartella"

        items = sorted((path.rglob if ricorsivo else path.glob)(pattern))
        if not items:
            return f"Cartella vuota: {path}"

        righe = [f"Cartella: {path}  ({len(items)} elementi)\n"]
        for item in items[:100]:
            rel   = item.relative_to(path)
            icona = "📁" if item.is_dir() else "📄"
            size  = f"  [{item.stat().st_size//1024:,} KB]" if item.is_file() else ""
            righe.append(f"  {icona} {rel}{size}")
        if len(items) > 100:
            righe.append(f"  ... e altri {len(items)-100} elementi")
        return "\n".join(righe)
    except PermissionError:
        return f"ERRORE: permesso negato per {percorso}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Crea una nuova cartella (e tutte le cartelle padre necessarie).",
    params={"percorso": {**S, "description": "Percorso completo della cartella da creare"}},
    required=["percorso"],
    label=("📁", "Creo la cartella"),
)
def crea_cartella(percorso: str) -> str:
    try:
        path = Path(percorso).expanduser().resolve()
        if path.exists():
            return f"La cartella esiste già: {path}"
        path.mkdir(parents=True, exist_ok=True)
        return f"✅ Cartella creata: {path}"
    except PermissionError:
        return f"ERRORE: permesso negato per {percorso}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description=(
        "Sposta tutti i file con una certa estensione da una cartella a un'altra. "
        "USA QUESTO per organizzare file in blocco. "
        "NON usare sposta_file con wildcard *.pdf — non funziona."
    ),
    params={
        "cartella":     {**S, "description": "Cartella origine (senza wildcard)"},
        "estensione":   {**S, "description": "Estensione es: '.pdf' oppure 'pdf'"},
        "destinazione": {**S, "description": "Cartella destinazione"},
    },
    required=["cartella", "estensione", "destinazione"],
    label=("📦", "Sposto tutti i"),
)
def sposta_per_estensione(cartella: str, estensione: str, destinazione: str) -> str:
    try:
        src_dir  = Path(cartella).expanduser().resolve()
        dest_dir = Path(destinazione).expanduser().resolve()
        if not src_dir.exists():
            return f"ERRORE: cartella origine non trovata: {src_dir}"

        ext = estensione.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext

        file_list = [f for f in src_dir.iterdir() if f.is_file() and f.suffix.lower() == ext]
        if not file_list:
            return f"Nessun file {ext} trovato in {src_dir}"

        dest_dir.mkdir(parents=True, exist_ok=True)
        spostati, errori = [], []

        for f in file_list:
            dest_file = dest_dir / f.name
            if dest_file.exists():
                base, count = dest_file.stem, 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{base}_{count}{ext}"
                    count += 1
            try:
                shutil.move(str(f), str(dest_file))
                spostati.append(f.name)
            except Exception as e:
                errori.append(f"{f.name}: {e}")

        righe = [f"✅ Spostati {len(spostati)} file {ext}  →  {dest_dir}"]
        for n in spostati[:10]:
            righe.append(f"   • {n}")
        if len(spostati) > 10:
            righe.append(f"   ... e altri {len(spostati)-10}")
        if errori:
            righe.append(f"⚠️  Errori: {len(errori)}")
            for e in errori[:5]:
                righe.append(f"   • {e}")
        return "\n".join(righe)
    except PermissionError:
        return f"ERRORE: permesso negato su {cartella}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Sposta UN singolo file o cartella. Percorso ESATTO — no wildcard.",
    params={
        "origine":      {**S, "description": "Percorso origine esatto"},
        "destinazione": {**S, "description": "Percorso destinazione"},
    },
    required=["origine", "destinazione"],
    label=("➡️ ", "Sposto"),
)
def sposta_file(origine: str, destinazione: str) -> str:
    try:
        src  = Path(origine).expanduser().resolve()
        dest = Path(destinazione).expanduser().resolve()
        if not src.exists():
            return f"ERRORE: origine non trovata: {src}"
        if dest.is_dir():
            dest = dest / src.name
        if dest.exists():
            return f"ERRORE: destinazione già esistente: {dest}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return f"✅ Spostato: {src.name}  →  {dest}"
    except PermissionError:
        return "ERRORE: permesso negato"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Copia un file o cartella in un'altra posizione.",
    params={
        "origine":      S,
        "destinazione": S,
    },
    required=["origine", "destinazione"],
    label=("📋", "Copio"),
)
def copia_file(origine: str, destinazione: str) -> str:
    try:
        src  = Path(origine).expanduser().resolve()
        dest = Path(destinazione).expanduser().resolve()
        if not src.exists():
            return f"ERRORE: origine non trovata: {src}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(src), str(dest)) if src.is_dir() else shutil.copy2(str(src), str(dest))
        return f"✅ Copiato: {src}  →  {dest}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Rinomina un file o cartella.",
    params={
        "percorso":   {**S, "description": "Percorso del file/cartella"},
        "nuovo_nome": {**S, "description": "Nuovo nome (solo nome, non percorso completo)"},
    },
    required=["percorso", "nuovo_nome"],
    label=("✏️ ", "Rinomino"),
)
def rinomina_file(percorso: str, nuovo_nome: str) -> str:
    try:
        path  = Path(percorso).expanduser().resolve()
        nuovo = path.parent / nuovo_nome
        if not path.exists():
            return f"ERRORE: file non trovato: {path}"
        if nuovo.exists():
            return f"ERRORE: '{nuovo_nome}' esiste già"
        path.rename(nuovo)
        return f"✅ Rinominato: {path.name}  →  {nuovo_nome}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Elimina un file o cartella. IRREVERSIBILE. Richiede conferma=true.",
    params={
        "percorso": S,
        "conferma": {**B, "description": "Deve essere true per procedere", "default": False},
    },
    required=["percorso"],
    label=("🗑️ ", "Elimino"),
)
def elimina_file(percorso: str, conferma: bool = False) -> str:
    if not conferma:
        return "⚠️  Passa conferma=true per procedere con l'eliminazione."
    try:
        path = Path(percorso).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: non trovato: {path}"
        shutil.rmtree(str(path)) if path.is_dir() else path.unlink()
        return f"✅ Eliminato: {path}"
    except PermissionError:
        return f"ERRORE: permesso negato per {percorso}"
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Cerca file per nome, estensione, contenuto o dimensione minima.",
    params={
        "cartella":          {**S, "description": "Cartella in cui cercare"},
        "nome":              {**S, "description": "Testo nel nome", "default": ""},
        "estensione":        {**S, "description": "Estensione es: '.pdf'", "default": ""},
        "contenuto":         {**S, "description": "Testo nel contenuto (file testo)", "default": ""},
        "dimensione_min_kb": {**I, "description": "Dimensione minima KB", "default": 0},
    },
    required=["cartella"],
    label=("🔎", "Cerco file in"),
)
def cerca_file(cartella: str, nome: str = "", estensione: str = "",
               contenuto: str = "", dimensione_min_kb: int = 0) -> str:
    try:
        path    = Path(cartella).expanduser().resolve()
        pattern = f"*{estensione}" if estensione else "*"
        results = []

        for item in path.rglob(pattern):
            if not item.is_file():
                continue
            if nome and nome.lower() not in item.name.lower():
                continue
            if dimensione_min_kb > 0 and item.stat().st_size < dimensione_min_kb * 1024:
                continue
            if contenuto:
                try:
                    if contenuto.lower() not in item.read_text(encoding="utf-8", errors="ignore").lower():
                        continue
                except Exception:
                    continue
            results.append(item)
            if len(results) >= 50:
                break

        if not results:
            return f"Nessun file trovato in {path}"

        righe = [f"Trovati {len(results)} file:\n"]
        for f in results:
            kb  = f.stat().st_size // 1024
            mod = __import__("datetime").datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y")
            righe.append(f"  📄 {f.relative_to(path)}  [{kb} KB]  {mod}")
        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Legge il contenuto di un file di testo (prime N righe).",
    params={
        "percorso":  {**S},
        "max_righe": {**I, "default": 50},
    },
    required=["percorso"],
    label=("📄", "Leggo il file"),
)
def leggi_file(percorso: str, max_righe: int = 50) -> str:
    try:
        path  = Path(percorso).expanduser().resolve()
        if not path.exists():
            return f"ERRORE: file non trovato: {path}"
        righe = path.read_text(encoding="utf-8", errors="replace").splitlines()
        testo = "\n".join(righe[:max_righe])
        if len(righe) > max_righe:
            testo += f"\n... ({len(righe)} righe totali)"
        return testo
    except Exception as e:
        return f"ERRORE: {e}"


@registry.tool(
    description="Restituisce info sul sistema operativo, cartella home, ecc.",
    params={},
    required=[],
    label=("💻", "Leggo info di sistema"),
)
def info_sistema() -> str:
    import platform
    from datetime import datetime
    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
        f"Home: {Path.home()}\n"
        f"CWD: {Path.cwd()}\n"
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
