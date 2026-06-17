# -*- mode: python ; coding: utf-8 -*-
"""
fileai.spec — Build PyInstaller per FileAI (GUI PyQt6)

Genera un eseguibile one-folder che include tutte le librerie necessarie e
copia il MANUALE_UTENTE nella cartella finale insieme all'eseguibile.

USO
    pip install pyinstaller
    pyinstaller fileai.spec

    # output: dist/FileAI/
    #   ├── FileAI(.exe)        ← eseguibile
    #   ├── MANUALE_UTENTE.md   ← manuale d'uso
    #   ├── README.md
    #   └── _internal/...       ← librerie e moduli

NOTE TECNICHE
    Il progetto NON è un package installato: i moduli (config.py, agent.py,
    registry.py, ecc.) stanno al root del repo e vengono caricati a runtime da
    gui/_bootstrap.py via importlib.util.spec_from_file_location, partendo da
    Path(__file__).parent.parent (= root del bundle). Per questo motivo:

      1. tutti i .py di root vanno inclusi come DATA al root del bundle, così
         _bootstrap.py li ritrova al loro percorso atteso;
      2. le loro dipendenze (ollama, anthropic, requests, pypdf, PIL) NON sono
         rilevabili dall'analisi statica di PyInstaller — perché importate
         dentro moduli caricati dinamicamente — e vanno aggiunte a mano come
         hiddenimports / collect_all.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── percorso del progetto ────────────────────────────────────────────────
# In un .spec, __file__ non è definito: usiamo la cwd da cui si lancia
# pyinstaller (cioè il root del repo).
ROOT = Path(SPECPATH)

# ── moduli .py di root caricati dinamicamente dal bootstrap ───────────────
# Vanno copiati nel bundle MANTENENDO il nome al top-level ('.').
_ROOT_PY = [
    "config.py", "registry.py", "pricing.py", "agent.py", "cli.py",
    "base.py", "ollama.py", "claude.py", "lmstudio.py",
    "filesystem.py", "analysis.py", "semantic.py", "health.py",
    "compression.py", "vision.py",
    "__init__.py",
]

datas = []
for _name in _ROOT_PY:
    _p = ROOT / _name
    if _p.exists():
        datas.append((str(_p), "."))

# file di accompagnamento che finiscono nella cartella dist
for _doc in ("MANUALE_UTENTE.md", "README.md", "CLAUDE.md"):
    _p = ROOT / _doc
    if _p.exists():
        datas.append((str(_p), "."))

# il package virtuale carica anche il sotto-package gui/: lo includiamo
for _g in (ROOT / "gui").glob("*.py"):
    datas.append((str(_g), "gui"))

# icona caricata a runtime per la finestra (oltre a quella dell'exe)
for _ico in ("icona.ico", "icona.png"):
    _p = ROOT / "assets" / _ico
    if _p.exists():
        datas.append((str(_p), "assets"))

# ── hidden imports + dati delle librerie di terze parti ───────────────────
hiddenimports = []
binaries = []

hiddenimports += collect_submodules("rich")
hiddenimports += collect_submodules("PyQt6")

# Librerie importate dentro i moduli caricati dinamicamente (non rilevabili
# automaticamente). collect_all è tollerante: se non installate, non rompe il
# build ma quel backend semplicemente non sarà disponibile a runtime.
for _pkg in ("ollama", "anthropic", "requests", "pypdf", "PIL", "certifi"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception as _e:  # pragma: no cover - dipende dall'ambiente di build
        print(f"[fileai.spec] pacchetto opzionale '{_pkg}' non incluso: {_e}")


block_cipher = None

a = Analysis(
    ["fileai_gui.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # moduli pesanti/inutili: escludili per alleggerire il bundle
    excludes=["tkinter", "matplotlib", "numpy", "PySide6", "PyQt5"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FileAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI: nessuna finestra console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icona.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FileAI",
)
