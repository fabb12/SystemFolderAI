"""
gui/main_window.py — Finestra principale FileAI GUI
"""

from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QUrl
from PyQt6.QtGui import QAction, QKeySequence, QFont, QTextCursor, QDragEnterEvent, QDropEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFileDialog, QInputDialog,
    QMessageBox, QFrame, QStatusBar,
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
    ("info",      "📊", "Analizza",         "Rapporto completo: tipi, salute, duplicati"),
    ("contenuti", "🧠", "Capire contenuti", "Spiega di cosa trattano i documenti"),
    ("backup",    "💾", "Backup",           "Crea un backup compresso della cartella"),
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
        self.setAcceptDrops(True)

        # config persistente
        self.cfg = load_gui_config()
        self._apply_env_from_cfg()

        # stato runtime
        self._worker: AgentWorker | None    = None
        self._thread: QThread | None        = None
        self._current_action                = "chat"
        self._running_action                = "chat"   # azione del worker attivo
        self._waiting_confirm               = False

        # stato del renderer di output (ragionamento multi-riga)
        self._thought_buffer: list[str]     = []
        self._in_thought                    = False

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
        c = COLORS
        self._append_html(
            f"<div style='color:{c['accent']}; font-size:16px; font-weight:600;'>"
            f"Benvenuto in FileAI</div>"
            f"<div style='color:{c['text_dim']}; margin-top:4px;'>"
            f"Seleziona un'azione a sinistra oppure scrivi una richiesta libera.<br>"
            f"Cartella attuale: <span style='color:{c['cyan']};'>"
            f"{escape(self.cfg['default_folder'])}</span>"
            f"</div>"
            f"<div style='color:{c['text_muted']}; margin-top:8px; font-size:11px;'>"
            f"💡 Trascina una cartella nella finestra per impostarla come target.<br>"
            f"⌨️  <b>Ctrl+,</b> Impostazioni · <b>Ctrl+L</b> Pulisci · <b>Ctrl+O</b> Apri cartella · <b>Ctrl+Q</b> Esci"
            f"</div><hr style='border:none; border-top:1px solid "
            f"{c['border']}; margin:12px 0;'>"
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
        # Limiti token: propagati come env per essere letti dai backend e da agent.py
        if self.cfg.get("ollama_num_ctx"):
            os.environ["OLLAMA_NUM_CTX"] = str(self.cfg["ollama_num_ctx"])
        if self.cfg.get("claude_max_tokens"):
            os.environ["CLAUDE_MAX_TOKENS"] = str(self.cfg["claude_max_tokens"])
        if self.cfg.get("lmstudio_max_tokens"):
            os.environ["LMSTUDIO_MAX_TOKENS"] = str(self.cfg["lmstudio_max_tokens"])
        if self.cfg.get("max_tool_chars"):
            os.environ["FILEAI_MAX_TOOL_CHARS"] = str(self.cfg["max_tool_chars"])
        if self.cfg.get("max_steps"):
            os.environ["FILEAI_MAX_STEPS"] = str(self.cfg["max_steps"])

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
            "contenuti": "Cartella di cui capire i contenuti (Invio = cartella corrente)",
            "backup":    "Cartella di cui fare backup (Invio = cartella corrente)",
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
        self._thought_buffer = []
        self._in_thought     = False
        self._chat.clear()
        self._welcome()

    def _about(self) -> None:
        QMessageBox.about(
            self, "Informazioni",
            "<b>FileAI</b><br>"
            "Gestione intelligente di file e cartelle con AI<br><br>"
            "<b>Backend:</b> Ollama · LM Studio · Claude API<br>"
            "<b>Tool:</b> organizzazione, ricerca, analisi semantica,<br>"
            "duplicati, salute, compressione, backup<br>"
            "<b>GUI:</b> PyQt6 · Tema Tokyo Night dark"
        )

    # ── Output rendering ───────────────────────────────────
    def _append_html(self, html: str) -> None:
        self._chat.moveCursor(QTextCursor.MoveOperation.End)
        self._chat.insertHtml(html)
        self._chat.append("")  # newline
        self._chat.moveCursor(QTextCursor.MoveOperation.End)

    def _flush_thought(self) -> None:
        """Renderizza il ragionamento accumulato come un blocco unico."""
        if not self._thought_buffer:
            self._in_thought = False
            return
        body = "\n".join(self._thought_buffer).strip()
        self._thought_buffer = []
        self._in_thought = False
        if not body:
            return
        c = COLORS
        self._append_html(
            f"<div style='margin:6px 0 6px 14px; padding:8px 12px; "
            f"background:{c['bg_alt']}; border-left:2px solid {c['border_soft']}; "
            f"border-radius:4px;'>"
            f"<div style='color:{c['text_muted']}; font-size:10px; "
            f"font-weight:700; text-transform:uppercase; letter-spacing:0.6px; "
            f"margin-bottom:4px;'>💭 Ragionamento</div>"
            f"<div style='color:{c['text_dim']}; font-style:italic;'>"
            f"{_md_to_html(body)}</div></div>"
        )

    def _append_line(self, raw: str) -> None:
        """
        Renderizza una riga dell'output dell'agente come blocchi puliti.

        Filtra il rumore tipico del rendering rich su terminale (frame `┌─│└─`,
        spinner `⏳ Elaborazione…`, righe vuote di cornice) e riconosce i
        marker semantici (header di step, ragionamento, azione tool, risultato).
        """
        c    = COLORS
        text = raw.rstrip()
        s    = text.strip()

        # 1) riga vuota → se siamo in un ragionamento multi-paragrafo la
        #    accumuliamo (preserva la struttura). Altrimenti non rendiamo nulla.
        if not s:
            if self._in_thought:
                self._thought_buffer.append("")
            return

        # 2) spinner residuale ("⏳ Elaborazione...") — in terminale verrebbe
        #    sovrascritto dal `\r`; qui lo scartiamo.
        if "Elaborazione" in s and ("⏳" in s or s.endswith("...")):
            return

        # 3) frame vuoto (solo `│` e spazi) → ignora
        if set(s) <= {"│", " "}:
            return

        # 4) divisore di rich con etichetta: "──── ripresa agente ────"
        m = re.match(r"^─+\s+(.+?)\s+─+\s*$", text)
        if m:
            self._flush_thought()
            self._append_html(
                f"<div style='color:{c['text_muted']}; font-size:10px; "
                f"text-transform:uppercase; letter-spacing:0.8px; "
                f"text-align:center; margin:10px 0 6px 0;'>"
                f"— {escape(m.group(1).strip())} —</div>"
            )
            return

        # 5) divisore puro (solo trattini) → linea sottile
        if set(s) <= {"─"}:
            self._flush_thought()
            self._append_html(
                f"<hr style='border:none; border-top:1px solid "
                f"{c['border']}; margin:8px 0;'>"
            )
            return

        # 6) header di step: "┌─ Step N ───…"
        m = re.match(r"^┌─\s*Step\s+(\d+).*$", text)
        if m:
            self._flush_thought()
            n = m.group(1)
            self._step_label.setText(f"Step {n}")
            self._append_html(
                f"<div style='margin:14px 0 4px 0; color:{c['accent']}; "
                f"font-weight:700; font-size:13px;'>"
                f"▸ Step {n}</div>"
            )
            return

        # 7) footer di step: "└─ completato in N step, X operazioni"
        m = re.match(r"^└─\s*(.+)$", text)
        if m:
            self._flush_thought()
            self._append_html(
                f"<div style='color:{c['text_muted']}; font-size:11px; "
                f"margin:2px 0 8px 14px;'>· {escape(m.group(1).strip())}</div>"
            )
            return

        # 8) ragionamento: "│  💭 <testo>" (può continuare su più righe)
        m = re.match(r"^│\s+💭\s*(.*)$", text)
        if m:
            self._flush_thought()
            self._in_thought = True
            body = re.sub(r"\[/?italic\]", "", m.group(1)).strip()
            if body:
                self._thought_buffer.append(body)
            return

        # 9) azione tool: "│  <icona> <descrizione>"
        m = re.match(r"^│\s+(.+)$", text)
        if m:
            self._flush_thought()
            body = m.group(1).strip()
            self._status_label.setText(body[:80])
            self._append_html(
                f"<div style='color:{c['cyan']}; margin:6px 0 2px 14px; "
                f"font-size:12px;'>→ {escape(body)}</div>"
            )
            return

        # 10) risultato del tool: riga indentata di 4+ spazi
        if raw.startswith("    "):
            self._flush_thought()
            body  = raw.lstrip().rstrip()
            color = c["text_dim"]
            if body.startswith("✅"):
                color = c["success"]
            elif body.startswith(("ERRORE", "⚠")):
                color = c["warning"]
            elif body.startswith("❌"):
                color = c["error"]
            elif body.startswith("..."):
                color = c["text_muted"]
            self._append_html(
                f"<div style='color:{color}; margin:1px 0 1px 32px; "
                f"font-family: ui-monospace, Menlo, Consolas, monospace; "
                f"font-size:11px; white-space: pre-wrap;'>"
                f"{escape(body)}</div>"
            )
            return

        # 11) se siamo dentro un ragionamento, accumula la riga (continuazione)
        if self._in_thought:
            self._thought_buffer.append(text)
            return

        # 12) default: messaggio generico (es. "🤖 Backend pronto", "⚠ Limite…")
        color = c["text"]
        if text.startswith("✅") or "completato" in text.lower():
            color = c["success"]
        elif text.startswith(("ERRORE", "⚠")):
            color = c["warning"]
        elif text.startswith("❌"):
            color = c["error"]
        elif text.startswith("🤖"):
            color = c["cyan"]
        elif text.startswith("⏸"):
            color = c["warning"]
        self._append_html(
            f"<div style='color:{color}; margin:2px 0; "
            f"white-space: pre-wrap;'>{escape(text)}</div>"
        )

    def _show_action_banner(self) -> None:
        """Mostra un banner nella chat con cartella e azione in corso."""
        c      = COLORS
        folder = self.cfg["default_folder"]
        meta   = {a[0]: a for a in QUICK_ACTIONS}.get(self._running_action)
        if not meta:
            return
        _, icon, label, _ = meta
        self._append_html(
            f"<div style='margin:10px 0 6px 0; padding:8px 14px; "
            f"background:{c['bg_panel']}; border-left:3px solid {c['accent']}; "
            f"border-radius:4px;'>"
            f"<span style='color:{c['accent']}; font-weight:700;'>{icon} {label}</span>"
            f"<span style='color:{c['text_dim']};'>  ·  {escape(folder)}</span>"
            f"</div>"
        )

    def _apri_cartella_output(self) -> None:
        """Apre la cartella corrente nel file manager del sistema."""
        folder = self.cfg["default_folder"]
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        if ok:
            self._info(f"📂 Cartella aperta: {folder}")
        else:
            self._info(f"⚠ Impossibile aprire la cartella: {folder}")

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

        if a == "contenuti":
            target = raw.strip() or folder
            return (
                f"Esegui analisi_semantica_cartella su '{target}'. "
                f"Spiega in modo chiaro di cosa trattano i documenti, "
                f"raggruppali per argomento e suggerisci come organizzarli per tema."
            )

        if a == "backup":
            target = raw.strip() or folder
            return (
                f"Crea un backup compresso della cartella '{target}' usando "
                f"crea_backup con compresso=true. Conferma la creazione e "
                f"riepiloga numero file e dimensione."
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
        self._running_action = self._current_action
        self._thought_buffer = []
        self._in_thought     = False

        self._send_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_label.setText("Elaborazione in corso…")
        self._step_label.setText("")

        # banner nella chat con la cartella e l'azione corrente
        self._show_action_banner()

        self._thread = QThread(self)
        self._worker = AgentWorker(
            prompt=prompt,
            model_spec=self.cfg["modello"],
            max_steps=int(self.cfg.get("max_steps", 60)),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.output.connect(self._append_line)
        self._worker.confirm.connect(self._on_confirm_request)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        # cleanup: quit il thread quando il worker ha finito, poi riabilita la UI
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def _on_finished(self, risposta: str) -> None:
        self._flush_thought()
        # FIX: disabilita Stop subito — non aspettare _on_thread_finished perché
        # tra i due segnali c'è un delay Qt visibile all'utente.
        self._stop_btn.setEnabled(False)
        self._step_label.setText("")
        if risposta and risposta.strip():
            self._agent_final(risposta)
        else:
            self._info("L'agente ha terminato senza una risposta testuale.")
        self._status_label.setText("Pronto")
        # apertura automatica della cartella per azioni che la modificano
        if self._running_action in ("organizza", "backup"):
            self._apri_cartella_output()

    def _on_failed(self, err: str) -> None:
        self._flush_thought()
        # FIX: stessa cosa — disabilita Stop immediatamente
        self._stop_btn.setEnabled(False)
        self._step_label.setText("")
        c = COLORS
        self._append_html(
            f"<div style='margin: 10px 0; padding: 10px 14px; "
            f"background:{c['bg_panel']}; border-left: 3px solid {c['error']}; "
            f"border-radius: 4px;'>"
            f"<div style='color:{c['error']}; font-weight:700;'>✗ Errore</div>"
            f"<div style='color:{c['text']}; white-space: pre-wrap;'>"
            f"{escape(err)}</div>"
            f"<div style='color:{c['text_muted']}; font-size:11px; margin-top:6px;'>"
            f"Apri <b>Impostazioni</b> per verificare modello, host e chiave API.</div>"
            f"</div>"
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
        self._stop_btn.setEnabled(False)   # ridondante ma sicuro
        self._step_label.setText("")
        self._input.setPlaceholderText("Scrivi una richiesta...  (Invio per inviare)")

    def _on_stop(self) -> None:
        if self._worker is not None and self._waiting_confirm:
            self._handle_confirm_reply("")  # annulla
            return
        if self._thread is not None:
            self._info("Stop richiesto (l'agente terminerà al prossimo step)")
            self._thread.requestInterruption()
            # NB: terminate() è ultima ratio — provoca crash se thread esegue I/O.
            # Lasciamo che il thread completi lo step corrente; l'utente può forzare
            # la chiusura della finestra se necessario.

    # ── Conferma interattiva ───────────────────────────────
    def _on_confirm_request(self, plan_text: str) -> None:
        self._flush_thought()
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

    # ── Drag & drop ────────────────────────────────────────
    def dragEnterEvent(self, ev: QDragEnterEvent) -> None:
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev: QDropEvent) -> None:
        urls = ev.mimeData().urls()
        if not urls:
            return
        paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
        if not paths:
            return

        # se è una cartella sola, la imposto anche come cartella di lavoro
        if len(paths) == 1 and Path(paths[0]).is_dir():
            self.cfg["default_folder"] = paths[0]
            from gui.settings_dialog import save_gui_config
            save_gui_config(self.cfg)
            self._folder_label.setText(self._folder_short())

        # inserisco i percorsi nel campo input (uno per riga se più di uno)
        if len(paths) == 1:
            self._input.setText(paths[0])
        else:
            self._input.setText(" ; ".join(paths))
        self._input.setFocus()
        self._info(f"📥  Trascinati {len(paths)} elemento/i")

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
