# -*- mode: python ; coding: utf-8 -*-
# PyInstaller .spec per FileAI
#
# Build:
#   pyinstaller fileai.spec --noconfirm
#
# Output:
#   dist/FileAI/FileAI(.exe)
#
# Note importanti:
#   I file .py al root del repo (agent.py, config.py, registry.py, ecc.) sono
#   caricati dinamicamente via gui/_bootstrap.py con importlib.spec_from_file_location.
#   Vanno quindi inclusi come DATA FILES, non come moduli importati.
#   In _bootstrap.py il repo_root è dedotto da __file__: quando l'app è
#   "frozen", Path(gui/_bootstrap.py).parent.parent punta a sys._MEIPASS,
#   dove PyInstaller estrae i datas → tutto funziona out-of-the-box.

from pathlib import Path

# ── File Python al root da bundlare come dati ─────────────────────
ROOT_PY_MODULES = [
    "config.py", "registry.py", "agent.py", "cli.py",
    "base.py", "ollama.py", "claude.py", "lmstudio.py",
    "filesystem.py", "analysis.py", "semantic.py", "health.py",
    "compression.py",
]

datas = [(m, ".") for m in ROOT_PY_MODULES if Path(m).exists()]
datas += [
    ("assets/icon.svg", "assets"),
    ("README.md", "."),
    ("CLAUDE.md", "."),
]

# ── Hidden imports ─────────────────────────────────────────────────
# Backend / dipendenze ottenute dinamicamente o caricate via importlib.
hiddenimports = [
    "PyQt6.QtSvg",
    "ollama",
    "anthropic",
    "rich",
    "requests",
    "pypdf",
    # tool registrati al boot via _bootstrap (referenziati come stringhe)
    "fileai.tools.filesystem",
    "fileai.tools.analysis",
    "fileai.tools.semantic",
    "fileai.tools.health",
    "fileai.tools.compression",
    "fileai.backends.base",
    "fileai.backends.ollama",
    "fileai.backends.claude",
    "fileai.backends.lmstudio",
    "fileai.agent",
    "fileai.config",
    "fileai.registry",
]

# ── Icona dell'eseguibile ──────────────────────────────────────────
# Su Windows serve .ico; su macOS .icns; su Linux PNG. Se manca, build comunque.
# Per generare assets/icon.ico da assets/icon.svg in modo veloce:
#   pip install cairosvg pillow
#   python -c "import cairosvg, io; from PIL import Image; \
#       d=cairosvg.svg2png(url='assets/icon.svg', output_width=256); \
#       Image.open(io.BytesIO(d)).save('assets/icon.ico', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
_icon = None
for cand in ("assets/icon.ico", "assets/icon.icns", "assets/icon.png"):
    if Path(cand).exists():
        _icon = cand
        break


block_cipher = None

a = Analysis(
    ["fileai_gui.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    console=False,        # nascondi terminale su Windows
    disable_windowed_traceback=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FileAI",
)
