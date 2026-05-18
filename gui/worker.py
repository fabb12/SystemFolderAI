"""
gui/worker.py — Worker thread che esegue l'agente FileAI
e inoltra l'output al thread principale via signal Qt.
"""

from __future__ import annotations

import io
import re

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


# ── ANSI strip ────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ── Stream Qt-aware ───────────────────────────────────────────────

class _SignalStream(io.TextIOBase):
    """
    File-like che inoltra ogni scrittura come signal Qt.
    Bufferizza per riga.
    """

    def __init__(self, emit_fn):
        super().__init__()
        self._emit  = emit_fn
        self._buf   = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._emit(_strip_ansi(line))
        return len(s)

    def flush(self) -> None:
        if self._buf:
            self._emit(_strip_ansi(self._buf))
            self._buf = ""


# ── Worker ────────────────────────────────────────────────────────

class AgentWorker(QObject):
    """
    Esegue run_agente in un thread separato.
    Emette signal per ogni evento (output, conferma, fine).
    """

    output       = pyqtSignal(str)         # riga di output
    confirm      = pyqtSignal(str)         # piano da confermare (testo)
    finished     = pyqtSignal(str)         # risposta finale
    failed       = pyqtSignal(str)         # eccezione

    def __init__(self, prompt: str, model_spec: str, max_steps: int = 30):
        super().__init__()
        self._prompt      = prompt
        self._model_spec  = model_spec
        self._max_steps   = max_steps
        self._confirm_ans: str | None = None
        self._confirm_thread: QThread | None = None

    @pyqtSlot(str)
    def provide_confirm(self, answer: str) -> None:
        """Chiamato dal main thread per sbloccare la conferma."""
        self._confirm_ans = answer

    def _wait_confirm(self, plan_text: str) -> str | None:
        """Blocca il worker finché il main thread non risponde."""
        self._confirm_ans = None
        self.confirm.emit(plan_text)

        # busy-wait con processEvents leggero
        while self._confirm_ans is None:
            QThread.msleep(80)

        ans = self._confirm_ans
        self._confirm_ans = None
        if ans == "__CANCEL__":
            return None
        return ans

    @pyqtSlot()
    def run(self) -> None:
        try:
            self._run_inner()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")

    def _run_inner(self) -> None:
        # bootstrap del package virtuale (idempotente)
        from gui._bootstrap import install as _install_fileai
        _install_fileai()

        # import locali per evitare import circolari e ritardare il caricamento
        from rich.console import Console
        from fileai import agent as agent_mod
        from fileai.backends import crea_backend

        # 1) sostituisco la console rich con una che scrive verso il signal
        stream = _SignalStream(self.output.emit)
        new_console = Console(file=stream, force_terminal=False,
                              color_system=None, width=120, soft_wrap=True)

        old_console = agent_mod.console
        old_confirm = agent_mod._chiedi_conferma_utente
        agent_mod.console = new_console

        # 2) sostituisco la funzione di conferma con una versione Qt
        def _gui_confirm(testo_agente: str):
            self.output.emit("")
            self.output.emit("⏸  In attesa di conferma...")
            ans = self._wait_confirm(testo_agente)
            if ans is None:
                self.output.emit("Operazione annullata dall'utente.")
                return None
            return ans

        agent_mod._chiedi_conferma_utente = _gui_confirm

        try:
            backend = crea_backend(self._model_spec)
            self.output.emit(f"🤖 Backend pronto: {backend}")
            risposta = agent_mod.run_agente(self._prompt, backend)
            self.finished.emit(risposta or "")
        finally:
            try:
                stream.flush()
            except Exception:
                pass
            agent_mod.console = old_console
            agent_mod._chiedi_conferma_utente = old_confirm
