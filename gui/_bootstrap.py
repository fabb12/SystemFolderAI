"""
gui/_bootstrap.py — Compatibility shim per il package `fileai`.

Nel repo i file (agent.py, config.py, registry.py, base.py, ollama.py,
claude.py, filesystem.py, analysis.py, semantic.py, health.py) sono al
root, ma il codice si importa fra loro come `from fileai.xxx import ...`
e con sotto-package `fileai.backends` e `fileai.tools`.

Questo modulo costruisce in `sys.modules` un package virtuale `fileai`
che mappa quei file e fornisce i sotto-package `backends` e `tools`
con i loro `__init__` (inclusa la funzione `crea_backend`).

Idempotente: chiamarlo più volte non fa danni.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


# moduli root → nome dentro il package virtuale
_ROOT_MODULES = {
    "config":   "fileai.config",
    "registry": "fileai.registry",
    "agent":    "fileai.agent",
}

# moduli root → nome dentro fileai.backends
_BACKEND_MODULES = {
    "base":     "fileai.backends.base",
    "ollama":   "fileai.backends.ollama",
    "claude":   "fileai.backends.claude",
    "lmstudio": "fileai.backends.lmstudio",
}

# moduli root → nome dentro fileai.tools
_TOOL_MODULES = {
    "filesystem":  "fileai.tools.filesystem",
    "analysis":    "fileai.tools.analysis",
    "semantic":    "fileai.tools.semantic",
    "health":      "fileai.tools.health",
    "compression": "fileai.tools.compression",
}


def _load(file_path: Path, full_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(full_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossibile caricare {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod  # prima di exec, per gestire import circolari
    spec.loader.exec_module(mod)
    return mod


def _make_pkg(name: str, root: Path) -> types.ModuleType:
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(root)]
    sys.modules[name] = pkg
    return pkg


def install(repo_root: Path | None = None) -> None:
    """Monta il package virtuale `fileai`. Idempotente."""
    if "fileai.agent" in sys.modules and "fileai.backends" in sys.modules:
        return

    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()

    # ── fileai (root package) ──
    if "fileai" not in sys.modules:
        _make_pkg("fileai", root)

    # ── moduli root piatti ──
    # ordine: config e registry prima (agent li importa)
    for fname in ("config", "registry"):
        full = _ROOT_MODULES[fname]
        if full not in sys.modules:
            _load(root / f"{fname}.py", full)
            setattr(sys.modules["fileai"], fname, sys.modules[full])

    # ── fileai.backends ──
    if "fileai.backends" not in sys.modules:
        bpkg = _make_pkg("fileai.backends", root)
        setattr(sys.modules["fileai"], "backends", bpkg)

    # backends.base prima (gli altri lo importano)
    for fname in ("base", "ollama", "claude", "lmstudio"):
        full = _BACKEND_MODULES[fname]
        src  = root / f"{fname}.py"
        if full not in sys.modules and src.exists():
            _load(src, full)
            setattr(sys.modules["fileai.backends"], fname, sys.modules[full])

    # crea_backend (manca nel repo, lo aggiungiamo qui)
    bpkg = sys.modules["fileai.backends"]
    if not hasattr(bpkg, "crea_backend"):
        def crea_backend(spec: str):
            from fileai.config import parse_modello
            kind, model = parse_modello(spec)
            if kind == "claude":
                from fileai.backends.claude import BackendClaude
                return BackendClaude(model)
            if kind == "lmstudio":
                from fileai.backends.lmstudio import BackendLMStudio
                return BackendLMStudio(model)
            from fileai.backends.ollama import BackendOllama
            return BackendOllama(model)
        bpkg.crea_backend = crea_backend  # type: ignore[attr-defined]

    # ── fileai.agent (dipende da registry) ──
    if "fileai.agent" not in sys.modules:
        _load(root / "agent.py", "fileai.agent")
        setattr(sys.modules["fileai"], "agent", sys.modules["fileai.agent"])

    # ── fileai.tools (auto-registrazione) ──
    if "fileai.tools" not in sys.modules:
        tpkg = _make_pkg("fileai.tools", root)
        setattr(sys.modules["fileai"], "tools", tpkg)

        for fname, full in _TOOL_MODULES.items():
            src = root / f"{fname}.py"
            if src.exists() and full not in sys.modules:
                try:
                    _load(src, full)
                    setattr(tpkg, fname, sys.modules[full])
                except Exception as e:
                    # non blocchiamo il bootstrap per un tool non disponibile
                    print(f"⚠️  Tool '{fname}' non caricato: {e}")
