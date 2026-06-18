"""
tools/compression.py — Compressione, estrazione e backup di cartelle
"""

from __future__ import annotations

import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

from fileai.registry import registry

S = {"type": "string"}
B = {"type": "boolean"}


def _journal(tipo: str, descrizione: str, passi_inversi: list[dict]) -> None:
    """Registra un'operazione reversibile nella cronologia (best-effort)."""
    try:
        from fileai.tools.history import registra_operazione
        registra_operazione(tipo, descrizione, passi_inversi)
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────

def _human_size(byte: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if byte < 1024 or unit == "GB":
            return f"{byte:.1f} {unit}"
        byte /= 1024
    return f"{byte:.1f} GB"


def _conta_contenuto(percorso: Path) -> tuple[int, int]:
    """Ritorna (numero_file, dimensione_totale_bytes)."""
    if percorso.is_file():
        return 1, percorso.stat().st_size
    n, dim = 0, 0
    for f in percorso.rglob("*"):
        if f.is_file():
            n += 1
            try:
                dim += f.stat().st_size
            except OSError:
                pass
    return n, dim


# ── Tool: comprime ────────────────────────────────────────────────

@registry.tool(
    description=(
        "Comprime un file o un'intera cartella in un archivio .zip. "
        "Se 'destinazione' è omessa, crea l'archivio accanto alla sorgente."
    ),
    params={
        "origine":      {**S, "description": "File o cartella da comprimere"},
        "destinazione": {**S, "description": "Percorso .zip di output (opzionale)", "default": ""},
    },
    required=["origine"],
    label=("🗜️ ", "Comprimo"),
)
def comprime_zip(origine: str, destinazione: str = "") -> str:
    try:
        src = Path(origine).expanduser().resolve()
        if not src.exists():
            return f"ERRORE: origine non trovata: {src}"

        if destinazione.strip():
            out = Path(destinazione).expanduser().resolve()
            if out.suffix.lower() != ".zip":
                out = out.with_suffix(".zip")
        else:
            out = src.parent / f"{src.name}.zip"

        if out.exists():
            return f"ERRORE: destinazione già esistente: {out}"

        out.parent.mkdir(parents=True, exist_ok=True)
        n_file, dim_orig = _conta_contenuto(src)

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if src.is_file():
                zf.write(src, src.name)
            else:
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(src.parent))

        dim_zip = out.stat().st_size
        ratio   = (1 - dim_zip / dim_orig) * 100 if dim_orig else 0
        _journal("comprime_zip", f"Creato archivio {out}",
                 [{"op": "rm", "path": str(out)}])
        return (
            f"✅ Archivio creato: {out}\n"
            f"   File compressi : {n_file}\n"
            f"   Originale      : {_human_size(dim_orig)}\n"
            f"   Archivio       : {_human_size(dim_zip)}\n"
            f"   Risparmio      : {ratio:.1f}%"
        )
    except PermissionError:
        return f"ERRORE: permesso negato su {origine}"
    except Exception as e:
        return f"ERRORE: {e}"


# ── Tool: estrai ──────────────────────────────────────────────────

@registry.tool(
    description=(
        "Estrae un archivio .zip, .tar, .tar.gz, .tgz, .tar.bz2 in una cartella. "
        "Se 'destinazione' è omessa, estrae in una cartella accanto all'archivio."
    ),
    params={
        "archivio":     {**S, "description": "Percorso dell'archivio da estrarre"},
        "destinazione": {**S, "description": "Cartella di destinazione (opzionale)", "default": ""},
    },
    required=["archivio"],
    label=("📂", "Estraggo"),
)
def estrai_archivio(archivio: str, destinazione: str = "") -> str:
    try:
        src = Path(archivio).expanduser().resolve()
        if not src.exists():
            return f"ERRORE: archivio non trovato: {src}"
        if not src.is_file():
            return f"ERRORE: '{src}' non è un file"

        nome_base = src.name
        for suff in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".zip", ".tar"):
            if nome_base.lower().endswith(suff):
                nome_base = nome_base[: -len(suff)]
                break

        out = Path(destinazione).expanduser().resolve() if destinazione.strip() \
              else src.parent / nome_base
        out.mkdir(parents=True, exist_ok=True)

        n_estratti = 0
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as zf:
                # Guard contro Zip Slip: rifiuta path che escono da out
                for member in zf.namelist():
                    target = (out / member).resolve()
                    try:
                        target.relative_to(out)
                    except ValueError:
                        return f"ERRORE: archivio contiene path sospetto: {member}"
                zf.extractall(out)
                n_estratti = len(zf.namelist())
        elif tarfile.is_tarfile(src):
            with tarfile.open(src) as tf:
                for member in tf.getmembers():
                    target = (out / member.name).resolve()
                    try:
                        target.relative_to(out)
                    except ValueError:
                        return f"ERRORE: archivio contiene path sospetto: {member.name}"
                tf.extractall(out)
                n_estratti = len(tf.getmembers())
        else:
            return f"ERRORE: formato non riconosciuto: {src.suffix}"

        return (
            f"✅ Estratti {n_estratti} elementi\n"
            f"   Archivio : {src}\n"
            f"   In       : {out}"
        )
    except PermissionError:
        return f"ERRORE: permesso negato su {archivio}"
    except (zipfile.BadZipFile, tarfile.TarError) as e:
        return f"ERRORE: archivio corrotto o illeggibile: {e}"
    except Exception as e:
        return f"ERRORE: {e}"


# ── Tool: backup datato ───────────────────────────────────────────

@registry.tool(
    description=(
        "Crea un backup datato di una cartella. "
        "Default: archivio .zip con timestamp nel nome accanto alla sorgente. "
        "Con 'compresso=false' fa una copia ricorsiva invece dello zip."
    ),
    params={
        "cartella":  {**S, "description": "Cartella da salvare"},
        "in_dove":   {**S, "description": "Dove salvare il backup (default: accanto)", "default": ""},
        "compresso": {**B, "description": "Se true crea uno zip, se false copia", "default": True},
    },
    required=["cartella"],
    label=("💾", "Backup di"),
)
def crea_backup(cartella: str, in_dove: str = "", compresso: bool = True) -> str:
    try:
        src = Path(cartella).expanduser().resolve()
        if not src.exists() or not src.is_dir():
            return f"ERRORE: cartella non valida: {src}"

        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir  = Path(in_dove).expanduser().resolve() if in_dove.strip() else src.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if compresso:
            out = dest_dir / f"{src.name}_backup_{ts}.zip"
            if out.exists():
                return f"ERRORE: backup già esistente: {out}"
            n_file, dim_orig = _conta_contenuto(src)
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(src.parent))
            _journal("crea_backup", f"Creato backup {out}",
                     [{"op": "rm", "path": str(out)}])
            return (
                f"✅ Backup compresso creato\n"
                f"   Archivio : {out}\n"
                f"   File     : {n_file}  ({_human_size(dim_orig)} originali)\n"
                f"   ZIP      : {_human_size(out.stat().st_size)}"
            )

        out = dest_dir / f"{src.name}_backup_{ts}"
        if out.exists():
            return f"ERRORE: backup già esistente: {out}"
        shutil.copytree(str(src), str(out))
        _journal("crea_backup", f"Creato backup (copia) {out}",
                 [{"op": "rm", "path": str(out)}])
        n_file, dim_orig = _conta_contenuto(out)
        return (
            f"✅ Backup (copia) creato\n"
            f"   Cartella : {out}\n"
            f"   File     : {n_file}  ({_human_size(dim_orig)})"
        )
    except PermissionError:
        return f"ERRORE: permesso negato"
    except Exception as e:
        return f"ERRORE: {e}"
