"""
gui/settings_dialog.py — Dialog impostazioni complete
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QPushButton, QTabWidget,
    QWidget, QFileDialog, QMessageBox,
)


GUI_CONFIG_PATH = Path.home() / ".fileai_gui.json"

DEFAULTS = {
    "modello":          "ollama:llama3.1",
    "ollama_host":      "http://localhost:11434",
    "lmstudio_host":    "http://localhost:1234",
    "claude_api_key":   "",
    "default_folder":   str(Path.home()),
    "max_steps":        60,
    "auto_confirm":     False,
    "font_size":        13,
    "ollama_num_ctx":   32768,
    "claude_max_tokens": 8192,
    "lmstudio_max_tokens": 8192,
    "max_tool_chars":   24000,
}


# ── Persistenza ───────────────────────────────────────────────────

def load_gui_config() -> dict:
    cfg = DEFAULTS.copy()
    try:
        if GUI_CONFIG_PATH.exists():
            cfg.update(json.loads(GUI_CONFIG_PATH.read_text()))
    except Exception:
        pass
    return cfg


def save_gui_config(cfg: dict) -> None:
    try:
        GUI_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as e:
        print(f"⚠️  Impossibile salvare config GUI: {e}")


# ── Dialog ────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Dialog impostazioni con sezioni a tab."""

    MODEL_CHOICES = [
        "ollama:llama3.1",
        "ollama:qwen2.5",
        "ollama:mistral-nemo",
        "claude",
        "claude:sonnet",
        "claude:opus",
        "claude:haiku",
        "lmstudio",
    ]

    @staticmethod
    def _scopri_modelli_locali(ollama_host: str, lmstudio_host: str) -> list[str]:
        """Cerca i modelli installati localmente su Ollama e LM Studio."""
        trovati: list[str] = []
        try:
            from fileai.backends.ollama import lista_modelli_disponibili as _ol
            for n in _ol(ollama_host):
                trovati.append(f"ollama:{n}")
        except Exception:
            pass
        try:
            from fileai.backends.lmstudio import lista_modelli_disponibili as _lm
            for n in _lm(lmstudio_host):
                trovati.append(f"lmstudio:{n}")
        except Exception:
            pass
        return trovati

    def __init__(self, parent=None, current: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni FileAI")
        self.setMinimumSize(560, 480)
        self._cfg = (current or load_gui_config()).copy()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(12)

        title = QLabel("⚙  Impostazioni")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._tab_model(),    "Modello AI")
        tabs.addTab(self._tab_general(),  "Generale")
        tabs.addTab(self._tab_advanced(), "Avanzate")
        root.addWidget(tabs, 1)

        # bottoni in basso
        btns = QHBoxLayout()
        btns.addStretch(1)
        reset = QPushButton("Ripristina default")
        reset.setObjectName("DangerBtn")
        reset.clicked.connect(self._on_reset)
        cancel = QPushButton("Annulla")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Salva")
        ok.setObjectName("PrimaryBtn")
        ok.setDefault(True)
        ok.clicked.connect(self._on_save)
        btns.addWidget(reset)
        btns.addSpacing(20)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        root.addLayout(btns)

    # ── Tab Modello ────────────────────────────────────────
    def _tab_model(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        # gruppo selettore modello
        gb = QGroupBox("Modello di default")
        f = QFormLayout(gb)
        row = QHBoxLayout()
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.addItems(self.MODEL_CHOICES)
        self.cb_model.setCurrentText(self._cfg["modello"])
        row.addWidget(self.cb_model, 1)
        self.btn_rescan = QPushButton("🔄 Rileva")
        self.btn_rescan.setToolTip("Cerca modelli installati su Ollama e LM Studio")
        self.btn_rescan.clicked.connect(self._rileva_modelli)
        row.addWidget(self.btn_rescan)
        wrap = QWidget(); wrap.setLayout(row)
        f.addRow(self._label("Spec modello"), wrap)
        hint = QLabel("Es: ollama:llama3.1, claude, claude:opus, lmstudio:<id>")
        hint.setObjectName("HelpText")
        f.addRow("", hint)
        self.lbl_scoperti = QLabel("")
        self.lbl_scoperti.setObjectName("HelpText")
        self.lbl_scoperti.setWordWrap(True)
        f.addRow("", self.lbl_scoperti)
        layout.addWidget(gb)

        # gruppo Ollama
        gb_o = QGroupBox("Ollama (modelli locali)")
        f_o = QFormLayout(gb_o)
        self.ed_ollama = QLineEdit(self._cfg["ollama_host"])
        self.ed_ollama.setPlaceholderText("http://localhost:11434")
        f_o.addRow(self._label("Host"), self.ed_ollama)
        oh = QLabel("Avvia con: ollama serve")
        oh.setObjectName("HelpText")
        f_o.addRow("", oh)
        layout.addWidget(gb_o)

        # gruppo LM Studio
        gb_lm = QGroupBox("LM Studio (modelli locali, API OpenAI)")
        f_lm = QFormLayout(gb_lm)
        self.ed_lmstudio = QLineEdit(self._cfg.get("lmstudio_host", "http://localhost:1234"))
        self.ed_lmstudio.setPlaceholderText("http://localhost:1234")
        f_lm.addRow(self._label("Host"), self.ed_lmstudio)
        lh = QLabel("Avvia il server in LM Studio: Developer → Start Server")
        lh.setObjectName("HelpText")
        f_lm.addRow("", lh)
        layout.addWidget(gb_lm)

        # gruppo Claude
        gb_c = QGroupBox("Claude API")
        f_c = QFormLayout(gb_c)
        self.ed_key = QLineEdit(self._cfg["claude_api_key"])
        self.ed_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_key.setPlaceholderText("sk-ant-...")
        f_c.addRow(self._label("API Key"), self.ed_key)
        ch = QLabel("Necessaria per usare i modelli claude:*")
        ch.setObjectName("HelpText")
        f_c.addRow("", ch)
        layout.addWidget(gb_c)

        layout.addStretch(1)
        return w

    # ── Tab Generale ───────────────────────────────────────
    def _tab_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        gb = QGroupBox("Cartella di lavoro")
        f = QFormLayout(gb)
        row = QHBoxLayout()
        self.ed_folder = QLineEdit(self._cfg["default_folder"])
        row.addWidget(self.ed_folder, 1)
        browse = QPushButton("Sfoglia…")
        browse.clicked.connect(self._pick_folder)
        row.addWidget(browse)
        wrap = QWidget(); wrap.setLayout(row)
        f.addRow(self._label("Default"), wrap)
        layout.addWidget(gb)

        gb_a = QGroupBox("Comportamento")
        f_a = QFormLayout(gb_a)
        self.cb_autoconfirm = QCheckBox("Conferma automatica delle azioni (sconsigliato)")
        self.cb_autoconfirm.setChecked(self._cfg["auto_confirm"])
        f_a.addRow("", self.cb_autoconfirm)
        layout.addWidget(gb_a)

        layout.addStretch(1)
        return w

    # ── Tab Avanzate ───────────────────────────────────────
    def _tab_advanced(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        gb = QGroupBox("Esecuzione agente")
        f = QFormLayout(gb)
        self.sp_steps = QSpinBox()
        self.sp_steps.setRange(5, 500)
        self.sp_steps.setValue(self._cfg["max_steps"])
        f.addRow(self._label("Step massimi"), self.sp_steps)
        sh = QLabel("Iterazioni massime del loop ReAct (default 60). "
                    "Aumenta per task lunghi.")
        sh.setObjectName("HelpText")
        sh.setWordWrap(True)
        f.addRow("", sh)

        self.sp_tool_chars = QSpinBox()
        self.sp_tool_chars.setRange(2000, 200000)
        self.sp_tool_chars.setSingleStep(1000)
        self.sp_tool_chars.setValue(self._cfg["max_tool_chars"])
        self.sp_tool_chars.setSuffix("  caratteri")
        f.addRow(self._label("Output max per tool"), self.sp_tool_chars)
        th = QLabel("Tronca i risultati dei tool prima di rimandarli al modello "
                    "(default 24000). Più alto = più contesto = task lunghi più stabili.")
        th.setObjectName("HelpText")
        th.setWordWrap(True)
        f.addRow("", th)
        layout.addWidget(gb)

        gb_tk = QGroupBox("Finestra di contesto / token")
        f_tk = QFormLayout(gb_tk)

        self.sp_ollama_ctx = QSpinBox()
        self.sp_ollama_ctx.setRange(4096, 131072)
        self.sp_ollama_ctx.setSingleStep(2048)
        self.sp_ollama_ctx.setValue(self._cfg["ollama_num_ctx"])
        self.sp_ollama_ctx.setSuffix("  token")
        f_tk.addRow(self._label("Ollama num_ctx"), self.sp_ollama_ctx)

        self.sp_claude_tok = QSpinBox()
        self.sp_claude_tok.setRange(1024, 64000)
        self.sp_claude_tok.setSingleStep(512)
        self.sp_claude_tok.setValue(self._cfg["claude_max_tokens"])
        self.sp_claude_tok.setSuffix("  token")
        f_tk.addRow(self._label("Claude max_tokens"), self.sp_claude_tok)

        self.sp_lmstudio_tok = QSpinBox()
        self.sp_lmstudio_tok.setRange(512, 64000)
        self.sp_lmstudio_tok.setSingleStep(512)
        self.sp_lmstudio_tok.setValue(self._cfg["lmstudio_max_tokens"])
        self.sp_lmstudio_tok.setSuffix("  token")
        f_tk.addRow(self._label("LM Studio max_tokens"), self.sp_lmstudio_tok)

        h = QLabel("Aumenta la finestra se task lunghi vengono troncati. "
                   "I modelli locali piccoli o con poca RAM richiedono valori più bassi.")
        h.setObjectName("HelpText")
        h.setWordWrap(True)
        f_tk.addRow("", h)
        layout.addWidget(gb_tk)

        gb_ui = QGroupBox("Interfaccia")
        f_ui = QFormLayout(gb_ui)
        self.sp_font = QSpinBox()
        self.sp_font.setRange(10, 22)
        self.sp_font.setValue(self._cfg["font_size"])
        self.sp_font.setSuffix("  px")
        f_ui.addRow(self._label("Dimensione font"), self.sp_font)
        layout.addWidget(gb_ui)

        info = QLabel(
            "Le impostazioni vengono salvate in:\n"
            f"  {GUI_CONFIG_PATH}\n"
            f"  {Path.home() / '.fileai.json'} (modello di default CLI)"
        )
        info.setObjectName("HelpText")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch(1)
        return w

    # ── Helpers ────────────────────────────────────────────
    @staticmethod
    def _label(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("FormLabel")
        return lab

    def _pick_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Scegli cartella di lavoro",
            self.ed_folder.text() or str(Path.home())
        )
        if d:
            self.ed_folder.setText(d)

    def _rileva_modelli(self) -> None:
        """Cerca i modelli locali e li aggiunge al combo."""
        self.btn_rescan.setEnabled(False)
        self.btn_rescan.setText("…")
        try:
            ol_host = self.ed_ollama.text().strip() or "http://localhost:11434"
            lm_host = self.ed_lmstudio.text().strip() or "http://localhost:1234"
            trovati = self._scopri_modelli_locali(ol_host, lm_host)

            # aggiorna il combo conservando il valore corrente
            corrente = self.cb_model.currentText()
            esistenti = {self.cb_model.itemText(i) for i in range(self.cb_model.count())}
            nuovi = [m for m in trovati if m not in esistenti]
            for m in nuovi:
                self.cb_model.addItem(m)
            if corrente:
                self.cb_model.setCurrentText(corrente)

            if not trovati:
                self.lbl_scoperti.setText(
                    "Nessun modello locale rilevato.\n"
                    "Avvia 'ollama serve' o LM Studio (Start Server) e riprova."
                )
            else:
                ol_n = sum(1 for m in trovati if m.startswith("ollama:"))
                lm_n = sum(1 for m in trovati if m.startswith("lmstudio:"))
                self.lbl_scoperti.setText(
                    f"Rilevati {ol_n} modelli Ollama e {lm_n} modelli LM Studio."
                )
        finally:
            self.btn_rescan.setEnabled(True)
            self.btn_rescan.setText("🔄 Rileva")

    def _on_reset(self) -> None:
        if QMessageBox.question(
            self, "Conferma",
            "Ripristino le impostazioni di default?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self._cfg = DEFAULTS.copy()
        # ricarico campi
        self.cb_model.setCurrentText(self._cfg["modello"])
        self.ed_ollama.setText(self._cfg["ollama_host"])
        self.ed_lmstudio.setText(self._cfg["lmstudio_host"])
        self.ed_key.setText(self._cfg["claude_api_key"])
        self.ed_folder.setText(self._cfg["default_folder"])
        self.cb_autoconfirm.setChecked(self._cfg["auto_confirm"])
        self.sp_steps.setValue(self._cfg["max_steps"])
        self.sp_tool_chars.setValue(self._cfg["max_tool_chars"])
        self.sp_ollama_ctx.setValue(self._cfg["ollama_num_ctx"])
        self.sp_claude_tok.setValue(self._cfg["claude_max_tokens"])
        self.sp_lmstudio_tok.setValue(self._cfg["lmstudio_max_tokens"])
        self.sp_font.setValue(self._cfg["font_size"])

    def _on_save(self) -> None:
        self._cfg = {
            "modello":             self.cb_model.currentText().strip() or DEFAULTS["modello"],
            "ollama_host":         self.ed_ollama.text().strip()       or DEFAULTS["ollama_host"],
            "lmstudio_host":       self.ed_lmstudio.text().strip()     or DEFAULTS["lmstudio_host"],
            "claude_api_key":      self.ed_key.text().strip(),
            "default_folder":      self.ed_folder.text().strip()       or DEFAULTS["default_folder"],
            "max_steps":           int(self.sp_steps.value()),
            "auto_confirm":        self.cb_autoconfirm.isChecked(),
            "font_size":           int(self.sp_font.value()),
            "ollama_num_ctx":      int(self.sp_ollama_ctx.value()),
            "claude_max_tokens":   int(self.sp_claude_tok.value()),
            "lmstudio_max_tokens": int(self.sp_lmstudio_tok.value()),
            "max_tool_chars":      int(self.sp_tool_chars.value()),
        }
        save_gui_config(self._cfg)

        # propaga: env per ollama, lmstudio e claude
        if self._cfg["claude_api_key"]:
            os.environ["ANTHROPIC_API_KEY"] = self._cfg["claude_api_key"]
        os.environ["OLLAMA_HOST"]          = self._cfg["ollama_host"]
        os.environ["LMSTUDIO_HOST"]        = self._cfg["lmstudio_host"]
        os.environ["OLLAMA_NUM_CTX"]       = str(self._cfg["ollama_num_ctx"])
        os.environ["CLAUDE_MAX_TOKENS"]    = str(self._cfg["claude_max_tokens"])
        os.environ["LMSTUDIO_MAX_TOKENS"]  = str(self._cfg["lmstudio_max_tokens"])
        os.environ["FILEAI_MAX_TOOL_CHARS"] = str(self._cfg["max_tool_chars"])
        os.environ["FILEAI_MAX_STEPS"]     = str(self._cfg["max_steps"])

        try:
            from fileai.config import set_default_modello
            set_default_modello(self._cfg["modello"])
        except Exception:
            pass

        self.accept()

    def values(self) -> dict:
        return self._cfg
