#!/usr/bin/env python3
"""
fileai_gui — entry point GUI PyQt6 dark mode

Avvia con:
    python fileai_gui.py

Requisiti:
    pip install PyQt6
    (oltre alle dipendenze base: ollama / anthropic / rich)
"""
import sys
from pathlib import Path

# aggiungi la cartella padre al path se si lancia da fuori del package
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication  # noqa: F401
    except ImportError:
        print("✗ PyQt6 non installato. Installa con:  pip install PyQt6")
        return 2

    # monta il package virtuale `fileai` mappando i file al root del repo
    from gui._bootstrap import install as _install_fileai
    _install_fileai()

    from gui.main_window import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
