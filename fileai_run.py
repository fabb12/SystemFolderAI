#!/usr/bin/env python3
"""
fileai — entry point
Avvia con: python fileai_run.py <comando> [opzioni]
"""
import sys
from pathlib import Path

# aggiungi la cartella padre al path se si lancia da fuori del package
sys.path.insert(0, str(Path(__file__).parent))

from fileai.cli import main

if __name__ == "__main__":
    main()
