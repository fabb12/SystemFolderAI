"""
gui/main_window.py — Finestra principale FileAI GUI
"""

from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QSize
from PyQt6.QtGui import QAction, QKeySequence, QFont, QTextCursor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QSplitter, QFileDialog, QInputDialog,
    QMessageBox, QToolButton, QFrame, QSizePolicy, QStatusBar,
)

from gui.styles import COLORS, dark_qss
from gui.worker import AgentWorker
from gui.settings_dialog import SettingsDialog, load_gui_config


# ── Quick actions sidebar ─────────────────────────────────────────

QUICK_ACTIONS = [
    # (id, icona, etichetta, descrizione)
    ("chat",      "💬", "Chat libera",      "Domanda in linguaggio naturale"),
    ("organizza", "📁", "Organizza",        "Riordina una cartella per tipo"),
    ("cerca",     "🔎", "Cerca",            "Trova file per nome o contenuto"),
    ("info",      "📊", "Analizza",         "Rapporto completo cartella"),
    ("crea",      "🏗",  "Crea struttura",  "Crea sottocartelle da descrizione"),
    ("salute",    "🩺", "Salute",           "Duplicati, vuoti, temporanei"),
]


# ── Markdown → HTML ───────────────────────────────────────────────

_MD_HEAD_RE   = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
_MD_NUM_RE    = re.compile(r"^\d+[.)]\s+(.*)$")


def _md_inline(s: str) -> str:
    """Converte gli elementi inline del Markdown (su testo già escapato)."""
    s = re.sub(r"`([^`]+)`",
               r"<code style='background:#00000040; padding:1px 4px; "
               r"border-radius:3px;'>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__([^_]+)__",     r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<i>\1</i>", s)
    return s


def _md_to_html(text: str) -> str:
    """
    Converte un sottoinsieme di Markdown in HTML per la chat: intestazioni,
    grassetto, corsivo, codice inline ed elenchi puntati/numerati.
    Le risposte dell'agente sono in Markdown e prima venivano mostrate come
    testo grezzo (## e ** visibili).
    """
    out: list[str] = []
    list_tag: str | None = None

    def chiudi_lista() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            chiudi_lista()
            continue

        m = _MD_HEAD_RE.match(line)
        if m:
            chiudi_lista()
            size = {1: "16px", 2: "15px", 3: "14px"}.get(len(m.group(1)), "13px")
            out.append(
                f"<div style='font-weight:700; font-size:{size}; "
                f"margin:8px 0 2px;'>{_md_inline(escape(m.group(2)))}</div>"
            )
            continue

        m = _MD_BULLET_RE.match(line)
        if m:
            if list_tag != "ul":
                chiudi_lista()
                out.append("<ul style='margin:2px 0 2px 6px;'>")
                list_tag = "ul"
            out.append(f"<li>{_md_inline(escape(m.group(1)))}</li>")
            continue

        m = _MD_NUM_RE.match(line)
        if m:
            if list_tag != "ol":
                chiudi_lista()
                out.append("<ol style='margin:2px 0 2px 6px;'>")
                list_tag = "ol"
            out.append(f"<li>{_md_inline(escape(m.group(1)))}</li>")
            continue

        chiudi_lista()
        out.append(f"<div>{_md_inline(escape(line))}</div>")

    chiudi_lista()
    return "".join(out)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileAI — Gestione intelligente con AI")
        self.resize(1180, 740)
        self.setMinimumSize(880, 560)

        # config persistente
        self.cfg = load_gui_config()
        self._apply_env_from_cfg()

        # stato runtime
        self._worker: AgentWorker | None    = None
        self._thread: QThread | None        = None
        self._current_action                = "chat"
        self._waiting_confirm               = False

        self._build_ui()
        self._apply_font_size(self.cfg.get("font_size", 13))

    # ── UI build ───────────────────────────────────────────
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        root.addWidget(self._build_sidebar(), 0)

        # main column (topbar + chat + input)
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._build_topbar(), 0)
        v.addWidget(self._build_chat_area(), 1)
        v.addWidget(self._build_input_bar(), 0)
        root.addWidget(col, 1)

        # status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_label = QLabel("Pronto")
        sb.addWidget(self._status_label, 1)
        self._step_label = QLabel("")
        sb.addPermanentWidget(self._step_label)

        # menu
        self._build_menu()

        self._welcome()

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(230)
        v = QVBoxLayout(side)
        v.setContentsMargins(0, 0, 0, 12)
        v.setSpacing(0)

        title = QLabel("FileAI")
        title.setObjectName("SidebarTitle")
        v.addWidget(title)

        sub = QLabel("Gestione file con AI")
        sub.setObjectName("SidebarSubtitle")
        v.addWidget(sub)

        # azioni rapide
        lab = QLabel("Azioni")
        lab.setObjectName("SidebarLabel")
        v.addWidget(lab)

        self._action_buttons: dict[str, QPushButton] = {}
        for aid, icon, label, desc in QUICK_ACTIONS:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setObjectName("SidebarBtn")
            btn.setCheckable(True)
            btn.setToolTip(desc)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, a=aid: self._select_action(a))
            v.addWidget(btn)
            self._action_buttons[aid] = btn

        self._action_buttons["chat"].setChecked(True)

        v.addStretch(1)

        # cartella corrente
        lab2 = QLabel("Cartella")
        lab2.setObjectName("SidebarLabel")
        v.addWidget(lab2)

        self._folder_label = QLabel(self._folder_short())
        self._folder_label.setStyleSheet(
            f"color: {COLORS['text_dim']}; padding: 0 16px; font-size: 11px;"
        )
        self._folder_label.setWordWrap(True)
        v.addWidget(self._folder_label)

        pick = QPushButton("  📂   Cambia cartella")
        pick.setObjectName("SidebarBtn")
        pick.setCursor(Qt.CursorShape.PointingHandCursor)
        pick.clicked.connect(self._pick_folder)
        v.addWidget(pick)

        # impostazioni
        lab3 = QLabel("Sistema")
        lab3.setObjectName("SidebarLabel")
        v.addWidget(lab3)

        st = QPushButton("  ⚙   Impostazioni")
        st.setObjectName("SidebarBtn")
        st.setCursor(Qt.CursorShape.PointingHandCursor)
        st.clicked.connect(self._open_settings)
        v.addWidget(st)

        cl = QPushButton("  🧹   Pulisci output")
        cl.setObjectName("SidebarBtn")
        cl.setCursor(Qt.CursorShape.PointingHandCursor)
        cl.clicked.connect(self._clear_chat)
        v.addWidget(cl)

        return side

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("Topbar")
        bar.setFixedHeight(46)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(10)

        self._action_title = QLabel("💬  Chat libera")
        self._action_title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 14px; font-weight: 600;"
        )
        h.addWidget(self._action_title)

        h.addStretch(1)

        h.addWidget(QLabel("Modello:", objectName="TopbarLabel"))
        self._model_pill = QLabel(self.cfg["modello"])
        self._model_pill.setObjectName("ModelPill")
        h.addWidget(self._model_pill)

        change = QPushButton("Cambia")
        change.clicked.connect(self._quick_model_change)
        h.addWidget(change)

        return bar

    def _build_chat_area(self) -> QWidget:
        self._chat = QTextEdit()
        self._chat.setObjectName("ChatView")
        self._chat.setReadOnly(True)
        self._chat.setFrameShape(QFrame.Shape.NoFrame)
        self._chat.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        return self._chat

    def _build_input_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("InputBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(8)

        self._browse_btn = QPushButton("📂")
        self._browse_btn.setToolTip("Scegli una cartella da inserire nella richiesta")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.setFixedWidth(40)
        self._browse_btn.clicked.connect(self._pick_folder_into_input)
        h.addWidget(self._browse_btn)

        self._input = QLineEdit()
        self._input.setObjectName("InputField")
        self._input.setPlaceholderText("Scrivi una richiesta...  (Invio per inviare)")
        self._input.returnPressed.connect(self._on_send)
        h.addWidget(self._input, 1)

        self._send_btn = QPushButton("Invia")
        self._send_btn.setObjectName("PrimaryBtn")
        self._send_btn.setMinimumWidth(96)
        self._send_btn.clicked.connect(self._on_send)
        h.addWidget(self._send_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("DangerBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        h.addWidget(self._stop_btn)

        return bar

    def _build_menu(self) -> None:
        mb = self.menuBar()
        file_m = mb.addMenu("&File")
        a_open = QAction("Apri cartella…", self)
        a_open.setShortcut(QKeySequence("Ctrl+O"))
        a_open.triggered.connect(self._pick_folder)
        file_m.addAction(a_open)
        file_m.addSeparator()
        a_quit = QAction("Esci", self)
        a_quit.setShortcut(QKeySequence("Ctrl+Q"))
        a_quit.triggered.connect(self.close)
        file_m.addAction(a_quit)

        edit_m = mb.addMenu("&Modifica")
        a_clear = QAction("Pulisci output", self)
        a_clear.setShortcut(QKeySequence("Ctrl+L"))
        a_clear.triggered.connect(self._clear_chat)
        edit_m.addAction(a_clear)

        tools_m = mb.addMenu("&Strumenti")
        a_set = QAction("Impostazioni…", self)
        a_set.setShortcut(QKeySequence("Ctrl+,"))
        a_set.triggered.connect(self._open_settings)
        tools_m.addAction(a_set)

        help_m = mb.addMenu("&Aiuto")
        a_about = QAction("Informazioni", self)
        a_about.triggered.connect(self._about)
        help_m.addAction(a_about)

    # ── Welcome / helpers ──────────────────────────────────
    def _welcome(self) -> None:
        self._append_html(
            f"<div style='color:{COLORS['accent']}; font-size:16px; font-weight:600;'>"
            f"Benvenuto in FileAI</div>"
            f"<div style='color:{COLORS['text_dim']}; margin-top:4px;'>"
            f"Seleziona un'azione a sinistra oppure scrivi una richiesta libera.<br>"
            f"Cartella attuale: <span style='color:{COLORS['cyan']};'>"
            f"{escape(self.cfg['default_folder'])}</span>"
            f"</div>"
            f"<div style='color:{COLORS['text_muted']}; margin-top:6px; font-size:11px;'>"
            f"Suggerimento: usa <b>Ctrl+,</b> per le impostazioni · "
            f"<b>Ctrl+L</b> per pulire l'output"
            f"</div><hr style='border:none; border-top:1px solid "
            f"{COLORS['border']}; margin:12px 0;'>"
        )

    def _folder_short(self) -> str:
        p = Path(self.cfg["default_folder"])
        try:
            return "~/" + str(p.relative_to(Path.home()))
        except ValueError:
            return str(p)

    def _apply_env_from_cfg(self) -> None:
        if self.cfg.get("claude_api_key"):
            os.environ["ANTHROPIC_API_KEY"] = self.cfg["claude_api_key"]
        if self.cfg.get("ollama_host"):
            os.environ["OLLAMA_HOST"] = self.cfg["ollama_host"]
        if self.cfg.get("lmstudio_host"):
            os.environ["LMSTUDIO_HOST"] = self.cfg["lmstudio_host"]

    def _apply_font_size(self, size: int) -> None:
        f = self._chat.font()
        f.setPointSize(max(9, int(size) - 1))
        self._chat.setFont(f)
        f2 = self._input.font()
        f2.setPointSize(max(9, int(size) - 1))
        self._input.setFont(f2)

    # ── Quick actions ──────────────────────────────────────
    def _select_action(self, action_id: str) -> None:
        self._current_action = action_id
        for aid, btn in self._action_buttons.items():
            btn.setChecked(aid == action_id)

        meta = {a[0]: a for a in QUICK_ACTIONS}[action_id]
        _, icon, label, desc = meta
        self._action_title.setText(f"{icon}  {label}")

        prompts = {
            "chat":      "Scrivi una richiesta...",
            "organizza": "Cartella da organizzare (Invio = cartella corrente)",
            "cerca":     "Cosa cerchi?  (es: 'relazione 2024')",
            "info":      "Cartella da analizzare (Invio = cartella corrente)",
            "crea":      "Struttura: es 'Django: app templates static docs'",
            "salute":    "Cartella da controllare (Invio = cartella corrente)",
        }
        self._input.setPlaceholderText(prompts.get(action_id, "..."))
        self._input.setFocus()

    def _pick_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Scegli cartella", self.cfg["default_folder"]
        )
        if not d:
            return
        self.cfg["default_folder"] = d
        from gui.settings_dialog import save_gui_config
        save_gui_config(self.cfg)
        self._folder_label.setText(self._folder_short())
        self._info(f"📂  Cartella impostata: {d}")

    def _pick_folder_into_input(self) -> None:
        """Apre un selettore cartelle e ne inserisce il percorso nel campo input."""
        start = self._input.text().strip() or self.cfg["default_folder"]
        d = QFileDialog.getExistingDirectory(self, "Scegli cartella", start)
        if not d:
            return
        self._input.setText(d)
        self._input.setFocus()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, current=self.cfg)
        if dlg.exec():
            self.cfg = dlg.values()
            self._apply_env_from_cfg()
            self._apply_font_size(self.cfg.get("font_size", 13))
            self._model_pill.setText(self.cfg["modello"])
            self._folder_label.setText(self._folder_short())
            self._info(f"⚙  Impostazioni salvate · modello: {self.cfg['modello']}")

    def _quick_model_change(self) -> None:
        from gui.settings_dialog import SettingsDialog
        scoperti = SettingsDialog._scopri_modelli_locali(
            self.cfg.get("ollama_host", "http://localhost:11434"),
            self.cfg.get("lmstudio_host", "http://localhost:1234"),
        )
        cloud = ["claude", "claude:sonnet", "claude:opus", "claude:haiku"]
        items = scoperti + cloud
        # ordina mantenendo locali prima
        seen: set[str] = set()
        items = [m for m in items if not (m in seen or seen.add(m))]
        if not items:
            items = ["ollama:llama3.1", "claude", "claude:haiku"]

        item, ok = QInputDialog.getItem(
            self, "Cambia modello",
            "Modello (locali rilevati + cloud):",
            items,
            current=items.index(self.cfg["modello"]) if self.cfg["modello"] in items else 0,
            editable=True,
        )
        if not ok or not item.strip():
            return
        self.cfg["modello"] = item.strip()
        from gui.settings_dialog import save_gui_config
        save_gui_config(self.cfg)
        self._model_pill.setText(self.cfg["modello"])
        try:
            from fileai.config import set_default_modello
            set_default_modello(self.cfg["modello"])
        except Exception:
            pass
        self._info(f"🤖  Modello: {self.cfg['modello']}")

    def _clear_chat(self) -> None:
        self._chat.clear()
        self._welcome()

    def _about(self) -> None:
        QMessageBox.about(
            self, "Informazioni",
            "<b>FileAI</b><br>Gestione intelligente di file e cartelle con AI<br>"
            "<br>Backend: Ollama (locale) o Claude API<br>"
            "GUI: PyQt6 · Tema: Tokyo Night dark"
        )

    # ── Output rendering ───────────────────────────────────
    def _append_html(self, html: str) -> None:
        self._chat.moveCursor(QTextCursor.MoveOperation.End)
        self._chat.insertHtml(html)
        self._chat.append("")  # newline
        self._chat.moveCursor(QTextCursor.MoveOperation.End)

    def _append_line(self, raw: str) -> None:
        """Renderizza una riga di output dell'agente con colori."""
        if raw == "":
            self._chat.append("")
            return

        text = raw.rstrip()
        c = COLORS
        # heuristics di colore
        if text.startswith("✅") or "completato" in text.lower():
            color = c["success"]
        elif text.startswith(("ERRORE", "⚠")):
            color = c["warning"]
        elif text.startswith("❌"):
            color = c["error"]
        elif "💭" in text:
            color = c["text_muted"]
        elif text.startswith(("┌", "└", "│", "─")) or "Step " in text:
            color = c["text_muted"]
        elif text.startswith("🤖"):
            color = c["cyan"]
        elif text.startswith("⏸"):
            color = c["warning"]
        else:
            color = c["text"]

        self._append_html(
            f"<div style='color:{color}; "
            f"font-family: ui-monospace, Menlo, Consolas, monospace; "
            f"white-space: pre-wrap;'>{escape(text)}</div>"
        )

    def _info(self, text: str) -> None:
        self._status_label.setText(text)
        self._append_html(
            f"<div style='color:{COLORS['text_muted']}; font-size:11px;'>· "
            f"{escape(text)}</div>"
        )

    def _user_bubble(self, text: str) -> None:
        c = COLORS
        self._append_html(
            f"<div style='margin: 10px 0 4px 0;'>"
            f"<span style='color:{c['accent']}; font-weight:700;'>Tu </span>"
            f"<span style='color:{c['text']};'>{escape(text)}</span>"
            f"</div>"
        )

    def _agent_final(self, text: str) -> None:
        c = COLORS
        self._append_html(
            f"<div style='margin: 14px 0 4px 0; padding: 10px 14px; "
            f"background:{c['bg_panel']}; border-left: 3px solid {c['success']}; "
            f"border-radius: 4px;'>"
            f"<div style='color:{c['success']}; font-weight:700; margin-bottom:4px;'>"
            f"✓ Risposta</div>"
            f"<div style='color:{c['text']};'>"
            f"{_md_to_html(text)}</div></div>"
        )

    # ── Send / agent loop ──────────────────────────────────
    def _build_prompt(self, raw: str) -> str:
        """Costruisce il prompt finale in base all'azione selezionata."""
        folder = self.cfg["default_folder"]
        a = self._current_action

        if a == "chat":
            return raw

        if a == "organizza":
            target = raw.strip() or folder
            return (
                f"Analizza la cartella '{target}': usa prima scansione_intelligente, "
                f"poi proponi un piano di organizzazione con sottocartelle per tipo, "
                f"aspetta conferma e poi esegui. Riassumi alla fine."
            )

        if a == "cerca":
            # se la richiesta contiene "in <path>" lasciamo all'agente; altrimenti aggiungiamo la cartella
            if not raw.strip():
                return f"Lista i file in '{folder}'."
            return (
                f"Cerca '{raw.strip()}' nella cartella '{folder}'. "
                f"Mostra percorsi completi, dimensioni e date."
            )

        if a == "info":
            target = raw.strip() or folder
            return (
                f"Analisi completa della cartella '{target}': usa analizza_cartella, "
                f"scansione_intelligente, controlla_salute_cartella, trova_duplicati. "
                f"Fornisci un rapporto completo con suggerimenti."
            )

        if a == "crea":
            return (
                f"Crea questa struttura di cartelle in '{folder}': {raw.strip()}. "
                f"Interpreta e crea tutte le cartelle necessarie. Elenca cosa hai creato."
            )

        if a == "salute":
            target = raw.strip() or folder
            return (
                f"Esegui controlla_salute_cartella e trova_duplicati su '{target}'. "
                f"Riassumi spazio recuperabile e file da rivedere."
            )

        return raw

    def _on_send(self) -> None:
        if self._worker is not None:
            # se stiamo aspettando una conferma, l'input diventa la risposta
            if self._waiting_confirm:
                text = self._input.text().strip()
                self._input.clear()
                self._handle_confirm_reply(text)
            return

        raw = self._input.text().strip()
        if not raw and self._current_action == "chat":
            return

        prompt = self._build_prompt(raw)
        self._input.clear()
        self._user_bubble(raw or f"({self._current_action} su {self._folder_short()})")
        self._start_worker(prompt)

    def _start_worker(self, prompt: str) -> None:
        self._send_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("Elaborazione in corso…")

        self._thread = QThread(self)
        self._worker = AgentWorker(
            prompt=prompt,
            model_spec=self.cfg["modello"],
            max_steps=int(self.cfg.get("max_steps", 30)),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.output.connect(self._append_line)
        self._worker.confirm.connect(self._on_confirm_request)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        # cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def _on_finished(self, risposta: str) -> None:
        if risposta and risposta.strip():
            self._agent_final(risposta)
        else:
            self._info("L'agente ha terminato senza una risposta testuale.")
        self._status_label.setText("Pronto")

    def _on_failed(self, err: str) -> None:
        c = COLORS
        self._append_html(
            f"<div style='margin: 10px 0; padding: 10px 14px; "
            f"background:{c['bg_panel']}; border-left: 3px solid {c['error']}; "
            f"border-radius: 4px;'>"
            f"<div style='color:{c['error']}; font-weight:700;'>✗ Errore</div>"
            f"<div style='color:{c['text']}; white-space: pre-wrap;'>"
            f"{escape(err)}</div></div>"
        )
        self._status_label.setText("Errore")

    def _on_thread_finished(self) -> None:
        if self._thread:
            self._thread.deleteLater()
        if self._worker:
            self._worker.deleteLater()
        self._thread = None
        self._worker = None
        self._waiting_confirm = False
        self._send_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._input.setPlaceholderText("Scrivi una richiesta...  (Invio per inviare)")

    def _on_stop(self) -> None:
        if self._worker is not None and self._waiting_confirm:
            self._handle_confirm_reply("")  # annulla
            return
        if self._thread is not None:
            self._info("Stop richiesto (l'agente terminerà al prossimo step)")
            # Non possiamo killare il thread Python in modo pulito; terminate è ultima ratio
            self._thread.requestInterruption()
            self._thread.terminate()

    # ── Conferma interattiva ───────────────────────────────
    def _on_confirm_request(self, plan_text: str) -> None:
        c = COLORS
        self._append_html(
            f"<div style='margin: 14px 0; padding: 10px 14px; "
            f"background:{c['bg_panel']}; border-left: 3px solid {c['warning']}; "
            f"border-radius: 4px;'>"
            f"<div style='color:{c['warning']}; font-weight:700; margin-bottom:6px;'>"
            f"⏸ L'agente attende conferma</div>"
            f"<div style='color:{c['text']};'>"
            f"{_md_to_html(plan_text)}</div></div>"
        )

        # autoconfirm
        if self.cfg.get("auto_confirm"):
            self._info("Conferma automatica attiva → procedo")
            self._handle_confirm_reply("Sì, procedi con il piano che hai proposto.")
            return

        self._waiting_confirm = True
        self._input.setPlaceholderText(
            "Rispondi:  s / sì / procedi   |   n / annulla   |   <testo per modificare>"
        )
        self._input.setFocus()
        self._status_label.setText("In attesa di conferma…")

    def _handle_confirm_reply(self, text: str) -> None:
        if not text or text.lower() in ("n", "no", "annulla", "stop", "esci"):
            self._info("Operazione annullata")
            answer = "__CANCEL__"
        elif text.lower() in ("s", "si", "sì", "ok", "y", "yes", "procedi", "vai", "continua"):
            answer = "Sì, procedi con il piano che hai proposto."
            self._info("✓ Confermato → procedo")
        else:
            answer = text
            self._info(f"↳ {text}")

        self._waiting_confirm = False
        self._input.setPlaceholderText("Elaborazione in corso…")
        self._status_label.setText("Elaborazione in corso…")
        if self._worker is not None:
            self._worker.provide_confirm(answer)

    # ── Close ──────────────────────────────────────────────
    def closeEvent(self, ev) -> None:
        if self._thread is not None and self._thread.isRunning():
            r = QMessageBox.question(
                self, "Chiusura",
                "L'agente è in esecuzione. Vuoi chiudere comunque?"
            )
            if r != QMessageBox.StandardButton.Yes:
                ev.ignore()
                return
            self._thread.terminate()
            self._thread.wait(1500)
        super().closeEvent(ev)


def run() -> int:
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("FileAI")
    app.setStyleSheet(dark_qss())
    # font di base
    f = QFont("Segoe UI")
    if not f.exactMatch():
        f = QFont()
    f.setPointSize(10)
    app.setFont(f)

    win = MainWindow()
    win.show()
    return app.exec()
