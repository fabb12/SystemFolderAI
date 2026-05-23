"""
fileai — Gestore intelligente di cartelle con AI
=================================================
Package structure:
    fileai/
    ├── __init__.py         esporta l'API pubblica
    ├── config.py           configurazione e parsing modello
    ├── registry.py         Tool Registry (pattern Plugin)
    ├── tools/
    │   ├── __init__.py     auto-registra tutti i tool
    │   ├── filesystem.py   operazioni su file e cartelle
    │   ├── analysis.py     analisi statistica e magic bytes
    │   ├── semantic.py     analisi semantica con LLM
    │   ├── health.py       duplicati, salute cartella
    │   └── compression.py  comprime/estrai archivi, backup
    ├── backends/
    │   ├── __init__.py     esporta i backend
    │   ├── base.py         interfaccia astratta Backend
    │   ├── ollama.py       backend Ollama
    │   ├── lmstudio.py     backend LM Studio
    │   └── claude.py       backend Claude API
    ├── agent.py            loop ReAct + conferma interattiva
    └── cli.py              argparse + comandi CLI
"""

from fileai.config import parse_modello, get_default_modello, modello_da_args
from fileai.registry import registry
from fileai.agent import run_agente
from fileai.backends import crea_backend

__all__ = [
    "parse_modello", "get_default_modello", "modello_da_args",
    "registry", "run_agente", "crea_backend",
]
