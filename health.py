"""
tools/health.py — Duplicati e salute della cartella
"""

import hashlib
from datetime import datetime
from pathlib import Path

from fileai.registry import registry

S = {"type": "string"}
I = {"type": "integer"}


# ── Tool: duplicati ───────────────────────────────────────────────

@registry.tool(
    description=(
        "Trova file duplicati. "
        "metodo='nome': stessi nomi (veloce). "
        "metodo='hash': stesso contenuto MD5 anche se rinominati (accurato). "
        "metodo='entrambi': entrambi i controlli."
    ),
    params={
        "cartella": S,
        "metodo":   {"type": "string", "enum": ["nome", "hash", "entrambi"], "default": "hash"},
    },
    required=["cartella"],
    label=("👯", "Cerco duplicati in"),
)
def trova_duplicati(cartella: str, metodo: str = "hash") -> str:

    def md5(path: Path) -> str:
        h = hashlib.md5()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "error"

    try:
        path      = Path(cartella).expanduser().resolve()
        file_list = [f for f in path.rglob("*") if f.is_file()]
        if not file_list:
            return "Nessun file trovato"

        righe  = [f"📁 Duplicati in: {path}  ({len(file_list)} file)\n"]
        totale = 0

        # ── per nome ─────────────────────────────────────────────
        if metodo in ("nome", "entrambi"):
            nomi: dict[str, list] = {}
            for f in file_list:
                nomi.setdefault(f.name.lower(), []).append(f)
            dup = {k: v for k, v in nomi.items() if len(v) > 1}
            if dup:
                righe.append(f"📛 DUPLICATI PER NOME ({len(dup)} gruppi):")
                for nome_f, paths in dup.items():
                    righe.append(f"  '{nome_f}':")
                    for p in paths:
                        kb  = p.stat().st_size // 1024
                        mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y")
                        righe.append(f"    • {p}  [{kb} KB]  {mod}")
                    totale += len(paths) - 1
            else:
                righe.append("📛 Nessun duplicato per nome\n")

        # ── per hash ──────────────────────────────────────────────
        if metodo in ("hash", "entrambi"):
            righe.append(f"🔑 Calcolo MD5 per {len(file_list)} file...")
            hmap: dict[str, list] = {}
            for f in file_list:
                hmap.setdefault(md5(f), []).append(f)
            dup = {k: v for k, v in hmap.items() if len(v) > 1 and k != "error"}
            if dup:
                spazio = sum(p[0].stat().st_size * (len(p)-1) for p in dup.values()) // 1024
                righe.append(f"🔑 DUPLICATI PER CONTENUTO ({len(dup)} gruppi):")
                for h, paths in dup.items():
                    kb  = paths[0].stat().st_size // 1024
                    righe.append(f"  Hash {h[:8]}...  ({kb} KB ciascuno):")
                    for p in paths:
                        mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y")
                        righe.append(f"    • {p}  {mod}")
                    totale += len(paths) - 1
                righe.append(f"\n  💾 Spazio recuperabile: {spazio:,} KB")
            else:
                righe.append("🔑 Nessun duplicato per contenuto")

        righe.append(f"\nCopie ridondanti totali: {totale}")
        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"


# ── Tool: salute cartella ─────────────────────────────────────────

@registry.tool(
    description=(
        "Controllo salute cartella: file temporanei, vuoti, "
        "molto grandi (>100MB), molto vecchi (>2 anni), nascosti, cartelle vuote."
    ),
    params={"cartella": S},
    required=["cartella"],
    label=("🏥", "Controllo salute di"),
)
def controlla_salute_cartella(cartella: str) -> str:
    try:
        path     = Path(cartella).expanduser().resolve()
        ora      = datetime.now().timestamp()
        DUE_ANNI = 2 * 365 * 24 * 3600
        EXT_TEMP = {".tmp", ".temp", ".bak", ".old", ".orig", ".swp", ".swo"}

        vecchi: list[str]     = []
        grandi: list[str]     = []
        vuoti: list[str]      = []
        nascosti: list[str]   = []
        temporanei: list[str] = []
        cart_vuote: list[str] = []

        for item in path.rglob("*"):
            if item.is_dir():
                try:
                    if not any(item.iterdir()):
                        cart_vuote.append(str(item.relative_to(path)))
                except Exception:
                    pass
                continue
            if not item.is_file():
                continue

            stat = item.stat()
            nome = item.name

            if stat.st_size == 0:
                vuoti.append(nome)
                continue

            if (ora - stat.st_mtime) > DUE_ANNI:
                mod  = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y")
                anni = int((ora - stat.st_mtime) / (365 * 24 * 3600))
                vecchi.append(f"{nome}  (ultima modifica {mod}, {anni} anni fa)")

            if stat.st_size > 100 * 1024 * 1024:
                grandi.append(f"{nome}  ({stat.st_size // (1024*1024)} MB)")

            if nome.startswith("."):
                nascosti.append(nome)

            if item.suffix.lower() in EXT_TEMP or nome.startswith("~$"):
                temporanei.append(f"{nome}  ({item.suffix})")

        righe = [f"🏥 Salute: {path}\n"]

        def sez(icona: str, titolo: str, lista: list, n: int = 10):
            if lista:
                righe.append(f"{icona} {titolo} ({len(lista)}):")
                for x in lista[:n]:
                    righe.append(f"   • {x}")
                if len(lista) > n:
                    righe.append(f"   ... e altri {len(lista)-n}")
                righe.append("")

        sez("🗑️ ", "File temporanei",       temporanei)
        sez("💀",  "File vuoti (0 byte)",   vuoti)
        sez("📦",  "File grandi (>100MB)",  grandi)
        sez("⏰",  "File vecchi (>2 anni)", vecchi)
        sez("👁️ ", "File nascosti",         nascosti)
        sez("📁",  "Cartelle vuote",        cart_vuote)

        if not any([temporanei, vuoti, grandi, vecchi, nascosti, cart_vuote]):
            righe.append("✅ Nessun problema rilevato")

        return "\n".join(righe)
    except Exception as e:
        return f"ERRORE: {e}"
