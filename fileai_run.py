#!/usr/bin/env python3
"""
fileai — entry point CLI
Avvia con: python fileai_run.py <comando> [opzioni]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Monta il package virtuale `fileai` mappando i file root.
from gui._bootstrap import install as _install_fileai
_install_fileai()

from fileai.cli import main

if __name__ == "__main__":
    main()
